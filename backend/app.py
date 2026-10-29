"""FastAPI 后端：登录认证 + AI 简历筛选 + 简历查询"""
import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import Agent
from auth import (
    hash_password,
    invalidate_user_tokens,
    login,
    logout,
    refresh_role,
    verify_token,
)
from connectors import email_connector
from db import (
    add_audit_log,
    count_active_admins,
    create_user,
    delete_candidate,
    filter_candidates,
    get_candidate,
    get_user,
    get_role_permissions,
    init_db,
    insert_candidate,
    list_audit_logs,
    list_email_logs,
    list_recommendations,
    list_users,
    purge_expired_candidates,
    set_role_permissions,
    update_candidate,
    update_candidate_status,
    update_interview,
    update_user,
)
from permissions import (
    ALL_PERMISSION_KEYS,
    DEFAULT_ROLE_PERMISSIONS,
    PERMISSION_GROUPS,
    PERMISSION_LABELS,
    ROLE_LABELS,
    ROLES,
    TECH_VISIBLE_STATUSES,
    can_transition,
    can_view_all_candidates,
    has_permission,
    transition_error,
)
from resume_parser import extract_contact, extract_resume_text
import vector_store

logger = logging.getLogger(__name__)

# 终态候选人（已通过/未通过）自动清理的巡检间隔（秒）
RETENTION_CHECK_SECONDS = 3600

# 启动时初始化数据库（建库建表 + 写入种子数据）
init_db()


def _retention_cleanup_once():
    """删除进入终态满 7 天的候选人档案（同步函数，放到线程里执行）"""
    try:
        ids = purge_expired_candidates()
        if ids:
            vector_store.invalidate()
    except Exception:
        logger.exception("自动清理过期候选人失败")


async def _retention_loop():
    """周期性清理终态候选人"""
    while True:
        await asyncio.sleep(RETENTION_CHECK_SECONDS)
        await asyncio.to_thread(_retention_cleanup_once)


@asynccontextmanager
async def lifespan(_app):
    """服务启动时拉起邮箱轮询，退出时停止（未配置 IMAP 时自动跳过）"""
    email_connector.start_scheduler()
    await asyncio.to_thread(_retention_cleanup_once)
    retention_task = asyncio.create_task(_retention_loop())
    try:
        yield
    finally:
        retention_task.cancel()
        with suppress(asyncio.CancelledError):
            await retention_task
        email_connector.stop_scheduler()


app = FastAPI(title="AI 简历筛选助手", lifespan=lifespan)

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


class InterviewReq(BaseModel):
    """面试安排与反馈（时间用 ISO 字符串，如 2026-11-02T14:00）"""

    interview_at: Optional[str] = None
    mode: Optional[str] = None
    interviewer: Optional[str] = None
    feedback: Optional[str] = None


class EmailConfigReq(BaseModel):
    host: str = ""
    port: int = 993
    user: str = ""
    password: str = ""
    mailbox: str = "INBOX"
    use_ssl: bool = True
    search_days: int = 7
    max_per_run: int = 50
    poll_interval: int = 300


class CandidateUpdate(BaseModel):
    name: str
    expected_position: str = ""
    skills: str = ""
    experience: str = ""
    education: str = ""
    phone: str = ""
    email: str = ""


class UserCreateReq(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "hr"


class UserUpdateReq(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


def current_actor(authorization: str = Header(None)) -> dict:
    """从请求头解析 token，返回 {username, display_name, role}"""
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    actor = verify_token(authorization.replace("Bearer ", ""))
    if not actor:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    return actor


def require_roles(*roles):
    """生成「仅限指定角色」的依赖：角色不匹配返回 403"""
    def dep(actor: dict = Depends(current_actor)) -> dict:
        if actor["role"] not in roles:
            names = "、".join(ROLE_LABELS.get(r, r) for r in roles)
            raise HTTPException(status_code=403, detail=f"该操作仅限{names}")
        return actor
    return dep


def require_perm(key):
    """生成「需要某项操作权限」的依赖：无权限返回 403"""
    def dep(actor: dict = Depends(current_actor)) -> dict:
        perms = get_role_permissions()
        if not has_permission(actor["role"], key, perms):
            raise HTTPException(
                status_code=403,
                detail=f"该操作需要「{PERMISSION_LABELS.get(key, key)}」权限，"
                "请联系管理员在「角色权限」中开通",
            )
        return actor
    return dep


# 复用同一份依赖集合，避免每个接口重复构造
ANY_ROLE = require_roles("admin", "hr", "tech")

CHAT_PERM = require_perm("ai.chat")
UPLOAD_PERM = require_perm("candidate.upload")
EDIT_PERM = require_perm("candidate.edit")
DELETE_PERM = require_perm("candidate.delete")
INTERVIEW_PERM = require_perm("interview.manage")
EMAIL_CONFIG_PERM = require_perm("email.config")
USERS_PERM = require_perm("users.manage")

# 账号与权限管理页面的操作日志类型
AUDIT_ACTION_LABELS = {
    "user.create": "新建账号",
    "user.role": "调整角色",
    "user.active": "启用 / 停用",
    "user.password": "重置密码",
    "user.profile": "修改姓名",
    "role.permissions": "修改角色权限",
}


def _log_audit(request: Request, actor: dict, action: str, target: str, detail: str = ""):
    """记录账号与权限管理操作（失败不影响主流程）"""
    add_audit_log(actor, action, target, detail, request.client.host if request.client else "")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/login")
def do_login(req: LoginReq):
    token, actor = login(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    role = actor["role"]
    allowed = (
        ALL_PERMISSION_KEYS
        if role == "admin"
        else get_role_permissions().get(role, set())
    )
    return {"token": token, **actor, "permissions": sorted(allowed)}


@app.get("/api/me")
def api_me(actor: dict = Depends(current_actor)):
    """刷新页面后用 token 换回当前账号、角色与已授权操作"""
    role = actor["role"]
    allowed = (
        ALL_PERMISSION_KEYS
        if role == "admin"
        else get_role_permissions().get(role, set())
    )
    return {**actor, "permissions": sorted(allowed)}


@app.post("/api/logout")
def api_logout(authorization: str = Header(None)):
    if authorization:
        logout(authorization.replace("Bearer ", ""))
    return {"status": "ok"}


def get_or_create_agent(username: str):
    """获取（或创建）某个用户的 Agent 会话"""
    agent = AGENTS.get(username)
    if agent is None:
        agent = Agent()
        AGENTS[username] = agent
    return agent


@app.post("/api/chat")
def chat(req: ChatReq, actor: dict = Depends(CHAT_PERM)):
    agent = get_or_create_agent(actor["username"])
    answer, tool_trace = agent.run(req.message)
    return {"answer": answer, "tool_trace": tool_trace}


@app.post("/api/chat/stream")
def chat_stream(req: ChatReq, actor: dict = Depends(CHAT_PERM)):
    """SSE 流式输出：逐段返回 AI 答复与工具调用轨迹"""
    agent = get_or_create_agent(actor["username"])

    def gen():
        try:
            for ev in agent.run_stream(req.message):
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:  # 流中途出错，返回错误事件
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/chat/reset")
def chat_reset(actor: dict = Depends(CHAT_PERM)):
    AGENTS.pop(actor["username"], None)
    return {"status": "ok"}


@app.get("/api/candidates")
def api_candidates(
    position: str | None = None,
    skills: str | None = None,
    education: str | None = None,
    min_years: int | None = None,
    actor: dict = Depends(ANY_ROLE),
):
    """候选人列表，支持按岗位/技能/学历/最低年限结构化筛选

    技术部只能看到 HR 已推送、尚未定论的候选人。
    """
    perms = get_role_permissions()
    statuses = None if can_view_all_candidates(actor["role"], perms) else TECH_VISIBLE_STATUSES
    return {
        "candidates": filter_candidates(
            position=position, skills=skills, education=education,
            min_years=min_years, statuses=statuses,
        )
    }


@app.get("/api/candidates/{cid}")
def api_candidate(cid: int, actor: dict = Depends(ANY_ROLE)):
    c = get_candidate(cid)
    if not c:
        raise HTTPException(status_code=404, detail="未找到该候选人")
    if (
        not can_view_all_candidates(actor["role"], get_role_permissions())
        and c["status"] not in TECH_VISIBLE_STATUSES
    ):
        raise HTTPException(status_code=403, detail="该候选人尚未推送到技术部，无权查看")
    return {"candidate": c}


@app.patch("/api/candidates/{cid}/status")
def api_update_status(cid: int, req: StatusReq, actor: dict = Depends(ANY_ROLE)):
    """更新候选人招聘流程状态，按角色授权校验阶段流转权限"""
    c = get_candidate(cid)
    if not c:
        raise HTTPException(status_code=404, detail="未找到该候选人")
    perms = get_role_permissions()
    if (
        not can_view_all_candidates(actor["role"], perms)
        and c["status"] not in TECH_VISIBLE_STATUSES
    ):
        raise HTTPException(status_code=403, detail="该候选人尚未推送到技术部，无权操作")
    from_status = c["status"] or "new"
    if req.status == from_status:
        return {"candidate": c}
    if not can_transition(actor["role"], from_status, req.status, perms):
        raise HTTPException(
            status_code=403,
            detail=transition_error(actor["role"], from_status, req.status),
        )
    try:
        update_candidate_status(cid, req.status, by_username=actor["username"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"candidate": get_candidate(cid)}


INTERVIEW_MODES = ("onsite", "video", "phone")


@app.patch("/api/candidates/{cid}/interview")
def api_update_interview(
    cid: int,
    req: InterviewReq,
    actor: dict = Depends(INTERVIEW_PERM),
):
    """安排面试并记录反馈（需要「安排面试与记录反馈」权限）"""
    c = get_candidate(cid)
    if not c:
        raise HTTPException(status_code=404, detail="未找到该候选人")
    if c["status"] not in TECH_VISIBLE_STATUSES:
        raise HTTPException(status_code=400, detail="候选人尚未进入技术评估环节，无法安排面试")

    interview_at = None
    if req.interview_at:
        try:
            interview_at = datetime.fromisoformat(req.interview_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="面试时间格式不正确")
    if req.mode and req.mode not in INTERVIEW_MODES:
        raise HTTPException(status_code=400, detail="面试形式不合法")

    updated = update_interview(
        cid,
        interview_at=interview_at,
        interview_mode=req.mode or "",
        interviewer=req.interviewer or "",
        feedback=req.feedback or "",
    )
    return {"candidate": updated}


@app.put("/api/candidates/{cid}")
def api_update_candidate(cid: int, req: CandidateUpdate, actor: dict = Depends(EDIT_PERM)):
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
def api_delete_candidate(cid: int, actor: dict = Depends(DELETE_PERM)):
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
    actor: dict = Depends(UPLOAD_PERM),
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
def api_recommendations(actor: dict = Depends(CHAT_PERM)):
    return {"recommendations": list_recommendations()}


@app.post("/api/ingest/email/run")
def api_ingest_email(actor: dict = Depends(UPLOAD_PERM)):
    """立即拉取一次邮箱简历（手动触发，与定时轮询共用同一把锁）"""
    try:
        return email_connector.run_ingest()
    except email_connector.EmailNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"邮箱拉取失败：{e}")


@app.get("/api/ingest/email/status")
def api_ingest_email_status(actor: dict = Depends(ANY_ROLE)):
    return email_connector.status()


@app.get("/api/ingest/email/config")
def api_email_config(actor: dict = Depends(EMAIL_CONFIG_PERM)):
    """邮箱绑定配置（不返回密码，只回 has_password）"""
    return email_connector.status()


@app.put("/api/ingest/email/config")
def api_save_email_config(req: EmailConfigReq, actor: dict = Depends(EMAIL_CONFIG_PERM)):
    """保存邮箱绑定配置，保存后立即生效并重启轮询"""
    if not req.host.strip() or not req.user.strip():
        raise HTTPException(status_code=400, detail="IMAP 服务器和邮箱账号不能为空")
    if not 1 <= req.port <= 65535:
        raise HTTPException(status_code=400, detail="端口需在 1~65535 之间")
    if req.search_days < 1 or req.poll_interval < 0 or req.max_per_run < 1:
        raise HTTPException(status_code=400, detail="回溯天数/同步间隔/单次上限取值不合法")
    return email_connector.save_settings(
        host=req.host, port=req.port, user=req.user, password=req.password,
        mailbox=req.mailbox, use_ssl=req.use_ssl, search_days=req.search_days,
        max_per_run=req.max_per_run, poll_interval=req.poll_interval,
    )


@app.post("/api/ingest/email/test")
def api_test_email_config(req: EmailConfigReq, actor: dict = Depends(EMAIL_CONFIG_PERM)):
    """用表单里的参数测试 IMAP 登录（未保存也可测）"""
    overrides = {
        "host": req.host.strip(), "port": req.port, "user": req.user.strip(),
        "password": req.password, "mailbox": req.mailbox,
        "use_ssl": req.use_ssl, "search_days": req.search_days,
    }
    try:
        return email_connector.test_connection(overrides)
    except email_connector.EmailNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"连接失败：{e}")


@app.get("/api/ingest/email/log")
def api_ingest_email_log(limit: int = 20, actor: dict = Depends(EMAIL_CONFIG_PERM)):
    return {"logs": list_email_logs(limit)}


def _public_user(u):
    """去掉密码哈希，只回账号与角色信息"""
    if not u:
        return u
    return {
        "id": u["id"],
        "username": u["username"],
        "display_name": u.get("display_name") or u["username"],
        "role": u["role"],
        "is_active": bool(u.get("is_active", 1)),
        "created_at": u.get("created_at"),
    }


@app.get("/api/users")
def api_users(actor: dict = Depends(USERS_PERM)):
    """账号列表（管理员）"""
    return {
        "users": [_public_user(u) for u in list_users()],
        "roles": [{"key": k, "label": v} for k, v in ROLE_LABELS.items()],
    }


@app.post("/api/users")
def api_create_user(
    req: UserCreateReq,
    request: Request,
    actor: dict = Depends(USERS_PERM),
):
    """新建账号（管理员）：账号名 + 初始密码 + 角色"""
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="账号不能为空")
    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效角色：{req.role}")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="初始密码至少 6 位")
    try:
        user = create_user(
            username, hash_password(req.password),
            req.display_name.strip() or username, req.role,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    _log_audit(
        request, actor, "user.create",
        f"{user['display_name']}（{user['username']}）",
        f"角色：{ROLE_LABELS.get(req.role, req.role)}；已设置初始密码",
    )
    return {"user": _public_user(user)}


@app.patch("/api/users/{uid}")
def api_update_user(
    uid: int,
    req: UserUpdateReq,
    request: Request,
    actor: dict = Depends(USERS_PERM),
):
    """改角色 / 停用启用 / 重置密码（管理员）"""
    target = get_user(uid)
    if not target:
        raise HTTPException(status_code=404, detail="未找到该账号")
    if req.role is not None and req.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效角色：{req.role}")
    if req.password is not None and req.password and len(req.password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")

    losing_admin = target["role"] == "admin" and (
        (req.role is not None and req.role != "admin") or req.is_active is False
    )
    if losing_admin and count_active_admins(exclude_user_id=uid) == 0:
        raise HTTPException(status_code=400, detail="至少需要保留一位启用的管理员")

    # 先算出变更内容，用于写入操作日志
    changes, action = [], None
    if req.role is not None and req.role != target["role"]:
        changes.append(
            f"角色 {ROLE_LABELS.get(target['role'], target['role'])}"
            f" → {ROLE_LABELS.get(req.role, req.role)}"
        )
        action = action or "user.role"
    if req.is_active is not None and bool(req.is_active) != bool(target["is_active"]):
        changes.append("状态 启用 → 停用" if not req.is_active else "状态 停用 → 启用")
        action = action or "user.active"
    if req.password:
        changes.append("重置登录密码")
        action = action or "user.password"
    new_name = req.display_name.strip() if req.display_name is not None else None
    if new_name and new_name != (target["display_name"] or ""):
        changes.append(f"姓名 {target['display_name'] or '—'} → {new_name}")
        action = action or "user.profile"

    updated = update_user(
        uid,
        role=req.role,
        is_active=req.is_active,
        password_hash=hash_password(req.password) if req.password else None,
        display_name=new_name,
    )
    # 停用或改密码后立即踢下线；仅改角色则同步更新其现有会话
    if req.is_active is False or req.password:
        invalidate_user_tokens(target["username"])
    elif req.role is not None:
        refresh_role(target["username"], req.role)
    if action:
        _log_audit(
            request, actor, action,
            f"{target['display_name']}（{target['username']}）",
            "；".join(changes),
        )
    return {"user": _public_user(updated)}


class RolePermReq(BaseModel):
    permissions: list[str] = []


@app.get("/api/roles/permissions")
def api_role_permissions(actor: dict = Depends(USERS_PERM)):
    """权限目录与各角色当前配置（管理员固定拥有全部权限）"""
    perms = get_role_permissions()
    return {
        "groups": PERMISSION_GROUPS,
        "roles": [
            {
                "key": key,
                "label": label,
                "locked": key == "admin",
                "permissions": sorted(
                    ALL_PERMISSION_KEYS if key == "admin" else perms.get(key, set())
                ),
                "defaults": sorted(
                    ALL_PERMISSION_KEYS
                    if key == "admin"
                    else set(DEFAULT_ROLE_PERMISSIONS.get(key, []))
                ),
                "user_count": sum(1 for u in list_users() if u["role"] == key),
            }
            for key, label in ROLE_LABELS.items()
        ],
    }


@app.put("/api/roles/{role}/permissions")
def api_set_role_permissions(
    role: str,
    req: RolePermReq,
    request: Request,
    actor: dict = Depends(USERS_PERM),
):
    """保存某个角色的操作权限（管理员不可修改）"""
    if role not in ROLES:
        raise HTTPException(status_code=400, detail=f"无效角色：{role}")
    if role == "admin":
        raise HTTPException(status_code=400, detail="管理员的权限固定为全部，不能修改")
    invalid = [k for k in req.permissions if k not in ALL_PERMISSION_KEYS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"包含无效权限项：{', '.join(invalid)}")

    old = get_role_permissions().get(role, set())
    set_role_permissions(role, req.permissions)
    latest = get_role_permissions().get(role, set())
    added, removed = sorted(latest - old), sorted(old - latest)
    if added or removed:
        parts = []
        if added:
            parts.append("开通 " + "、".join(PERMISSION_LABELS.get(k, k) for k in added))
        if removed:
            parts.append("关闭 " + "、".join(PERMISSION_LABELS.get(k, k) for k in removed))
        _log_audit(
            request, actor, "role.permissions",
            f"{ROLE_LABELS[role]}角色",
            "；".join(parts),
        )
    return {
        "role": role,
        "label": ROLE_LABELS[role],
        "permissions": sorted(latest),
    }


@app.get("/api/audit/logs")
def api_audit_logs(
    limit: int = 50,
    action: str = "",
    keyword: str = "",
    actor: dict = Depends(USERS_PERM),
):
    """账号与权限管理操作日志（管理员）"""
    return {
        "logs": list_audit_logs(limit, action or None, keyword.strip() or None),
        "actions": AUDIT_ACTION_LABELS,
    }


if __name__ == "__main__":
    # 可直接右键运行本文件启动后端；等价于 uvicorn app:app --port 8000
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)