"""读取配置文件与环境变量"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# 统一日志配置（可在 .env 里用 LOG_LEVEL 覆盖，如 DEBUG）
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
MODEL = os.getenv("MODEL", "Qwen/Qwen2.5-7B-Instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "resume_screener")

# —— IMAP 邮箱收件（招聘平台简历转发专用邮箱）——
IMAP_HOST = os.getenv("IMAP_HOST", "")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
IMAP_MAILBOX = os.getenv("IMAP_MAILBOX", "INBOX")
IMAP_USE_SSL = os.getenv("IMAP_USE_SSL", "true").lower() not in ("false", "0", "no")
# 每次同步回溯的邮件天数：覆盖「HR 已经点开过」的邮件，靠入库日志去重避免重复处理
IMAP_SEARCH_DAYS = int(os.getenv("IMAP_SEARCH_DAYS", "7"))
# 单次最多处理的邮件数，防止首次接入时一次性拉取过多
IMAP_MAX_PER_RUN = int(os.getenv("IMAP_MAX_PER_RUN", "50"))
# 定时轮询间隔（秒），0 表示只允许手动触发
IMAP_POLL_INTERVAL = int(os.getenv("IMAP_POLL_INTERVAL", "300"))