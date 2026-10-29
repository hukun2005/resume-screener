"""登录认证与 token 管理

token 存内存（演示用）：{token: {"username", "display_name", "role"}}。
生产环境应换成 Redis 或数据库持久化，并给 token 加过期时间。
"""
import hashlib
import secrets

from db import verify_user

TOKENS = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str):
    """校验账号密码，成功返回 (token, 账号信息)，失败返回 (None, None)"""
    user = verify_user(username, hash_password(password))
    if not user:
        return None, None
    token = secrets.token_hex(16)
    actor = {
        "username": user["username"],
        "display_name": user["display_name"] or user["username"],
        "role": user["role"],
    }
    TOKENS[token] = actor
    return token, actor


def verify_token(token: str):
    """根据 token 返回账号信息（含角色），无效返回 None"""
    return TOKENS.get(token)


def logout(token: str):
    TOKENS.pop(token, None)


def invalidate_user_tokens(username: str):
    """账号被改角色 / 停用 / 改密码后，立即踢掉其所有会话"""
    for token in [t for t, a in TOKENS.items() if a["username"] == username]:
        TOKENS.pop(token, None)


def refresh_role(username: str, role: str):
    """角色变更后同步更新该用户仍在使用的 token（下一请求即生效）"""
    for actor in TOKENS.values():
        if actor["username"] == username:
            actor["role"] = role
