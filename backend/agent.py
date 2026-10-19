"""AI 简历筛选 Agent：基于 LangGraph 的 ReAct 工具调用循环"""
import json

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

import config
from tools import AGENT_TOOLS

SYSTEM_PROMPT = """你是企业的 AI 简历筛选助手，帮助招聘者从简历库中筛选合适的候选人。

工作流程：
1. 理解招聘者的需求（岗位、技能要求、人数等）
2. 调用 search_candidates 工具从数据库检索匹配简历
3. 用简洁清晰的中文汇报推荐结果：候选人姓名、意向岗位、匹配度、推荐理由
4. 招聘者确认某位候选人后，调用 recommend_candidate 工具将其推荐给面试官

要求：回答简洁、条理清晰、只推荐数据库中真实存在的候选人，不要编造简历。"""

# 多轮对话历史管理：保留最近 MAX_TURNS 轮完整对话，更早的压缩为滚动摘要
MAX_TURNS = 8
SUMMARY_PROMPT = "把以下多轮对话压缩成一段不超过 100 字的中文摘要，重点保留：用户筛选简历的需求与技能关键词、已经推荐过的候选人姓名及推荐理由。"


def _parse_result(content):
    """把工具返回的内容尽量还原成结构化对象"""
    if isinstance(content, str):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content
    return content


def build_trace(messages):
    """从消息历史中提取工具调用轨迹（供前端刷新推荐列表）"""
    results = {}
    for m in messages:
        if isinstance(m, ToolMessage):
            results[m.tool_call_id] = m.content

    trace = []
    for m in messages:
        if isinstance(m, AIMessage) and m.tool_calls:
            for tc in m.tool_calls:
                trace.append({
                    "tool": tc["name"],
                    "args": tc["args"],
                    "result": _parse_result(results.get(tc["id"], "")),
                })
    return trace


def last_answer(messages):
    """取最后一条有文本内容的 AI 回复"""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content if isinstance(m.content, str) else str(m.content)
    return ""


class Agent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model=config.MODEL,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            temperature=0,
        )
        self.agent = create_react_agent(self.llm, AGENT_TOOLS)
        self.messages = [SystemMessage(content=SYSTEM_PROMPT)]
        self.summary = ""  # 更早对话的滚动摘要

    def _system_prompt(self):
        """返回带历史摘要的系统提示词"""
        if self.summary:
            return f"{SYSTEM_PROMPT}\n\n[历史对话摘要]\n{self.summary}"
        return SYSTEM_PROMPT

    def _conversation_text(self, messages):
        """把消息提炼成 user/assistant 纯对话文本（跳过系统消息与工具调用）"""
        lines = []
        for m in messages:
            if isinstance(m, SystemMessage):
                continue
            if isinstance(m, HumanMessage):
                lines.append(f"用户：{m.content}")
            elif isinstance(m, AIMessage) and m.content and not m.tool_calls:
                lines.append(f"助手：{m.content}")
        return "\n".join(lines)

    def _summarize(self, old_messages):
        """把旧对话（连同此前的摘要）滚动压缩成一段新摘要"""
        text = self._conversation_text(old_messages)
        if self.summary:
            text = f"[此前历史摘要]\n{self.summary}\n\n[本轮更早对话]\n{text}"
        if not text.strip():
            return ""
        resp = self.llm.invoke([
            SystemMessage(content=SUMMARY_PROMPT),
            HumanMessage(content=text),
        ])
        return resp.content if isinstance(resp.content, str) else str(resp.content)

    def _maybe_compress(self):
        """滑动窗口 + 摘要：历史超过 MAX_TURNS 轮时，把最早若干轮压缩为摘要"""
        user_idx = [i for i, m in enumerate(self.messages) if isinstance(m, HumanMessage)]
        if len(user_idx) <= MAX_TURNS:
            return
        cut = user_idx[len(user_idx) - MAX_TURNS]  # 保留最近 MAX_TURNS 轮
        old = self.messages[:cut]
        recent = self.messages[cut:]
        self.summary = self._summarize(old)
        self.messages = [SystemMessage(content=self._system_prompt())] + recent

    def run(self, user_input, max_steps=5):
        """执行一轮对话，返回 (文本回复, 工具调用轨迹)"""
        self.messages.append(HumanMessage(content=user_input))
        result = self.agent.invoke(
            {"messages": self.messages},
            config={"recursion_limit": max_steps * 2 + 1},
        )
        self.messages = list(result["messages"])
        self._maybe_compress()
        return last_answer(self.messages), build_trace(self.messages)

    def run_stream(self, user_input, max_steps=5):
        """流式执行一轮对话，逐段产出最终答复。

        生成器逐条产出事件字典：
          {"type": "delta", "content": "..."}   模型输出的文本片段
          {"type": "trace", "trace": [...]}     工具调用轨迹（用于前端刷新推荐列表）
          {"type": "done"}                       本次对话结束
        """
        self.messages.append(HumanMessage(content=user_input))
        final_state = None
        in_tool_call = False

        for mode, payload in self.agent.stream(
            {"messages": self.messages},
            config={"recursion_limit": max_steps * 2 + 1},
            stream_mode=["messages", "values"],
        ):
            if mode == "messages":
                chunk, _meta = payload
                if isinstance(chunk, AIMessageChunk):
                    if chunk.tool_call_chunks:
                        # 进入工具调用阶段，丢弃后续残留文本
                        in_tool_call = True
                        continue
                    if isinstance(chunk.content, str) and chunk.content:
                        if in_tool_call:
                            # 某些模型（如 Qwen）在工具参数后仍会输出 `}` `</tool_call>`
                            # 等标记，这些片段需丢弃，避免污染最终答复
                            continue
                        yield {"type": "delta", "content": chunk.content}
                elif isinstance(chunk, ToolMessage):
                    # 工具执行完成，退出工具调用阶段
                    in_tool_call = False
            elif mode == "values":
                final_state = payload

        self.messages = list(final_state["messages"]) if final_state else self.messages
        self._maybe_compress()
        yield {"type": "trace", "trace": build_trace(self.messages)}
        yield {"type": "done"}