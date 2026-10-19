"""FastAPI 后端：登录认证 + AI 简历筛选 + 简历查询"""
import json

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import Agent
from auth import login, verify_token
from db import get_candidate, init_db, insert_candidate, list_candidates, list_recommendations
from resume_parser import extract_resume_text
import vector_store

# 启动时初始化数据库（建库建表 + 写入种子数据）
init_db()

app = FastAPI(title="AI 简历筛选助手")

# 允许前端跨域访问（本地开发放开，生产环境应改成具体域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 每个登录用户的 Agent 会话（用于保持多轮对话上下文）
AGENTS = {}


class LoginReq(BaseModel):
    username: str
    password: str


class ChatReq(BaseModel):
    message: str


def current_user(authorization: str = Header(None)):
    """从请求头解析 token 并校验，返回用户名"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "")
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return username


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def do_login(req: LoginReq):
    token = login(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"token": token, "username": req.username}


def get_or_create_agent(username: str):
    """获取（或创建）某个用户的 Agent 会话"""
    agent = AGENTS.get(username)
    if agent is None:
        agent = Agent()
        AGENTS[username] = agent
    return agent


@app.post("/api/chat")
def chat(req: ChatReq, username: str = Depends(current_user)):
    agent = get_or_create_agent(username)
    answer, tool_trace = agent.run(req.message)
    return {"answer": answer, "tool_trace": tool_trace}


@app.post("/api/chat/stream")
def chat_stream(req: ChatReq, username: str = Depends(current_user)):
    """SSE 流式输出：逐段返回 AI 答复与工具调用轨迹"""
    agent = get_or_create_agent(username)

    def gen():
        try:
            for ev in agent.run_stream(req.message):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # 流中途出错，返回错误事件
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/chat/reset")
def chat_reset(username: str = Depends(current_user)):
    AGENTS.pop(username, None)
    return {"status": "ok"}


@app.get("/api/candidates")
def api_candidates(username: str = Depends(current_user)):
    return {"candidates": list_candidates()}


@app.get("/api/candidates/{cid}")
def api_candidate(cid: int, username: str = Depends(current_user)):
    c = get_candidate(cid)
    if not c:
        raise HTTPException(status_code=404, detail="未找到该候选人")
    return {"candidate": c}


@app.post("/api/candidates/upload")
async def upload_candidate(
    file: UploadFile = File(...),
    name: str = Form(...),
    expected_position: str = Form(""),
    username: str = Depends(current_user),
):
    """上传 PDF/Word 简历，自动提取文本并入库（A3）"""
    content = await file.read()
    text = extract_resume_text(content, file.filename)
    if not text:
        raise HTTPException(
            status_code=400,
            detail="无法解析该文件，请上传 PDF 或 Word（.docx）格式的简历",
        )
    # 取解析文本前 10 行作为简要技能/经历预览，正文全文存 resume_text
    skills_preview = text[:200]
    cid = insert_candidate(
        name=name,
        expected_position=expected_position,
        skills=skills_preview,
        resume_text=text,
    )
    vector_store.invalidate()  # 新增简历后失效向量索引，下次查询重建
    return {"candidate": get_candidate(cid)}


@app.get("/api/recommendations")
def api_recommendations(username: str = Depends(current_user)):
    return {"recommendations": list_recommendations()}


if __name__ == "__main__":
    # 可直接右键运行本文件启动后端；等价于 uvicorn app:app --port 8000
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)