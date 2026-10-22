"""FastAPI 后端：登录认证 + AI 简历筛选 + 简历查询"""
import json

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import Agent
from auth import login, verify_token
from db import (
    delete_candidate,
    filter_candidates,
    get_candidate,
    init_db,
    insert_candidate,
    list_recommendations,
    update_candidate,
    update_candidate_status,
)
from resume_parser import extract_contact, extract_resume_text
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


class StatusReq(BaseModel):
    status: str


class CandidateUpdate(BaseModel):
    name: str
    expected_position: str = ""
    skills: str = ""
    experience: str = ""
    education: str = ""
    phone: str = ""
    email: str = ""


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
def api_candidates(
    position: str | None = None,
    skills: str | None = None,
    education: str | None = None,
    min_years: int | None = None,
    username: str = Depends(current_user),
):
    """候选人列表，支持按岗位/技能/学历/最低年限结构化筛选"""
    return {
        "candidates": filter_candidates(
            position=position, skills=skills, education=education, min_years=min_years
        )
    }


@app.get("/api/candidates/{cid}")
def api_candidate(cid: int, username: str = Depends(current_user)):
    c = get_candidate(cid)
    if not c:
        raise HTTPException(status_code=404, detail="未找到该候选人")
    return {"candidate": c}


@app.patch("/api/candidates/{cid}/status")
def api_update_status(cid: int, req: StatusReq, username: str = Depends(current_user)):
    """更新候选人招聘流程状态（new/screening/interview/offered/rejected）"""
    c = get_candidate(cid)
    if not c:
        raise HTTPException(status_code=404, detail="未找到该候选人")
    try:
        update_candidate_status(cid, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"candidate": get_candidate(cid)}


@app.put("/api/candidates/{cid}")
def api_update_candidate(cid: int, req: CandidateUpdate, username: str = Depends(current_user)):
    """编辑候选人结构化信息（姓名/岗位/技能/经历/学历/联系方式）"""
    if not get_candidate(cid):
        raise HTTPException(status_code=404, detail="未找到该候选人")
    updated = update_candidate(
        cid,
        name=req.name,
        expected_position=req.expected_position,
        skills=req.skills,
        experience=req.experience,
        education=req.education,
        phone=req.phone,
        email=req.email,
    )
    vector_store.invalidate()  # 技能/岗位变化会影响向量，失效后重建
    return {"candidate": updated}


@app.delete("/api/candidates/{cid}")
def api_delete_candidate(cid: int, username: str = Depends(current_user)):
    """删除候选人及其关联推荐记录"""
    if not get_candidate(cid):
        raise HTTPException(status_code=404, detail="未找到该候选人")
    delete_candidate(cid)
    vector_store.invalidate()
    return {"status": "ok"}


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
    # 取解析文本前 200 字作为简要技能/经历预览，正文全文存 resume_text
    skills_preview = text[:200]
    contact = extract_contact(text)
    cid = insert_candidate(
        name=name,
        expected_position=expected_position,
        skills=skills_preview,
        resume_text=text,
        phone=contact["phone"],
        email=contact["email"],
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