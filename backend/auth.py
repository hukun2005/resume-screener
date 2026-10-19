"""登录认证与 token 管理"""
import hashlib
import secrets

from db import verify_user

# 内存 token 存储（演示用；生产环境应改用 Redis 或数据库持久化）
TOKENS = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str):
    """校验账号密码，成功返回 token，失败返回 None"""
    if not verify_user(username, hash_password(password)):
        return None
    token = secrets.token_hex(16)
    TOKENS[token] = username
    return token


def verify_token(token: str):
    """根据 token 返回用户名，无效返回 None"""
    return TOKENS.get(token)