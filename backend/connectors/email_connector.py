"""IMAP 邮箱收件适配器

招聘平台（BOSS直聘 / 智联 / 猎聘 / 前程无忧等）的「简历转发到邮箱」功能，
都会把候选人简历以 PDF / Word 附件发到 HR 邮箱。因此不需要平台 API 授权，
读取一个专用邮箱即可完成简历汇聚。

配置来源优先级：页面保存的 email_config 表 > backend/.env 默认值。
页面改动后立即生效（轮询线程会按新配置重启）。

处理流程：
    连接 IMAP → 按时间窗口检索邮件 → 抽取 PDF/DOCX 附件 → 解析正文
    → 手机号/邮箱查重 → 写入 candidates → 记录处理日志（幂等）
"""
import email
import hashlib
import imaplib
import logging
import re
import threading
from datetime import datetime, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr

from config import (
    IMAP_HOST,
    IMAP_MAILBOX,
    IMAP_MAX_PER_RUN,
    IMAP_PASSWORD,
    IMAP_POLL_INTERVAL,
    IMAP_PORT,
    IMAP_SEARCH_DAYS,
    IMAP_USE_SSL,
    IMAP_USER,
)
from db import (
    email_log_exists,
    find_candidate_by_contact,
    get_email_config,
    insert_candidate,
    insert_email_log,
    save_email_config,
)
from resume_parser import extract_contact, extract_resume_text
import vector_store

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = (".pdf", ".docx")

# .env 里的默认配置（页面保存过的值会覆盖它）
_ENV_DEFAULTS = {
    "host": IMAP_HOST,
    "port": IMAP_PORT,
    "user": IMAP_USER,
    "password": IMAP_PASSWORD,
    "mailbox": IMAP_MAILBOX,
    "use_ssl": IMAP_USE_SSL,
    "search_days": IMAP_SEARCH_DAYS,
    "max_per_run": IMAP_MAX_PER_RUN,
    "poll_interval": IMAP_POLL_INTERVAL,
}

# 只有一次同步能同时在跑（后台轮询与手动触发共用）
_run_lock = threading.Lock()
_stop_event = threading.Event()
_scheduler_thread = None
# 最近一次同步的状态，供接口查询
_last_run = {"at": None, "result": None, "error": None}

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class EmailNotConfigured(RuntimeError):
    """IMAP 相关配置缺失"""


def load_settings():
    """合并配置：页面保存值 > .env 默认值"""
    cfg = dict(_ENV_DEFAULTS)
    cfg["source"] = "env"
    row = get_email_config()
    if row:
        cfg["host"] = row["host"] or cfg["host"]
        cfg["port"] = row["port"] or cfg["port"]
        cfg["user"] = row["imap_user"] or cfg["user"]
        cfg["password"] = row["password"] or cfg["password"]
        cfg["mailbox"] = row["mailbox"] or cfg["mailbox"]
        cfg["use_ssl"] = bool(row["use_ssl"])
        cfg["search_days"] = row["search_days"] or cfg["search_days"]
        cfg["max_per_run"] = row["max_per_run"] or cfg["max_per_run"]
        cfg["poll_interval"] = row["poll_interval"]
        cfg["source"] = "db"
    return cfg


def save_settings(host, port, user, password="", mailbox="INBOX",
                  use_ssl=True, search_days=7, max_per_run=50, poll_interval=300):
    """保存页面配置并立即生效（重启轮询线程）"""
    existing = get_email_config()
    pwd = password or (existing["password"] if existing else IMAP_PASSWORD)
    save_email_config(
        host=host.strip(), port=int(port), imap_user=user.strip(), password=pwd,
        mailbox=(mailbox or "INBOX").strip(), use_ssl=bool(use_ssl),
        search_days=int(search_days), max_per_run=int(max_per_run),
        poll_interval=int(poll_interval),
    )
    restart_scheduler()
    return status()


def is_configured(cfg=None):
    cfg = cfg or load_settings()
    return bool(cfg["host"] and cfg["user"] and cfg["password"])


def status():
    """当前配置与最近一次同步状态（不回传密码）"""
    cfg = load_settings()
    return {
        "configured": is_configured(cfg),
        "source": cfg["source"],
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "has_password": bool(cfg["password"]),
        "mailbox": cfg["mailbox"],
        "use_ssl": cfg["use_ssl"],
        "search_days": cfg["search_days"],
        "max_per_run": cfg["max_per_run"],
        "poll_interval": cfg["poll_interval"],
        "running": _run_lock.locked(),
        "last_run": _last_run,
    }


def test_connection(overrides=None):
    """用传入的表单值（缺省回退已保存配置）验证 IMAP 登录与收件箱是否可用"""
    cfg = dict(load_settings())
    if overrides:
        for key in ("host", "port", "user", "mailbox", "use_ssl",
                    "search_days", "max_per_run", "poll_interval"):
            if overrides.get(key) not in (None, ""):
                cfg[key] = overrides[key]
        if overrides.get("password"):
            cfg["password"] = overrides["password"]
    if not is_configured(cfg):
        raise EmailNotConfigured("请先填写邮箱账号、IMAP 服务器和授权码")

    conn = _connect(cfg)
    try:
        typ, data = conn.select(cfg["mailbox"])
        if typ != "OK":
            raise RuntimeError(f"无法打开收件箱 {cfg['mailbox']}：{data}")
        typ, data = conn.uid("SEARCH", None, f'(SINCE "{_imap_date(cfg["search_days"])}")')
        recent = len(data[0].split()) if typ == "OK" and data and data[0] else 0
        return {"ok": True, "mailbox": cfg["mailbox"], "recent_messages": recent}
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            conn.logout()
        except Exception:
            pass


def run_ingest(cfg=None):
    """执行一次邮箱同步，返回统计结果

    未配置抛 EmailNotConfigured；并发执行抛 RuntimeError；网络错误向上抛出。
    """
    cfg = cfg or load_settings()
    if not is_configured(cfg):
        raise EmailNotConfigured(
            "未配置邮箱，请在页面「邮箱配置」中填写 IMAP 服务器、账号与授权码"
        )
    if not _run_lock.acquire(blocking=False):
        raise RuntimeError("已有一次邮箱同步正在进行，请稍后再试")
    try:
        result = _do_ingest(cfg)
        _last_run.update({"at": datetime.now().isoformat(timespec="seconds"),
                          "result": result, "error": None})
        return result
    except Exception as e:
        _last_run.update({"at": datetime.now().isoformat(timespec="seconds"),
                          "result": None, "error": str(e)})
        raise
    finally:
        _run_lock.release()


def _do_ingest(cfg):
    stats = {
        "fetched": 0,          # 检索到的邮件数
        "ingested": 0,         # 新增候选人
        "duplicate": 0,        # 库中已存在的候选人
        "skipped": 0,          # 已处理过的邮件附件
        "unsupported": 0,      # 非 PDF/DOCX 附件
        "failed": 0,           # 解析失败
        "no_attachment": 0,    # 邮件里没有可识别的简历附件
        "errors": [],
    }
    conn = _connect(cfg)
    try:
        conn.select(cfg["mailbox"])
        uids = _search_uids(conn, cfg["search_days"])
        stats["fetched"] = len(uids)
        for uid in uids[:cfg["max_per_run"]]:
            try:
                _process_message(conn, uid, stats)
            except Exception as e:
                logger.exception("处理邮件 uid=%s 失败", uid)
                stats["failed"] += 1
                if len(stats["errors"]) < 20:
                    stats["errors"].append(f"uid {uid}: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
        try:
            conn.logout()
        except Exception:
            pass

    if stats["ingested"]:
        vector_store.invalidate()  # 简历库有新增，下次检索重建索引
    stats["finished_at"] = datetime.now().isoformat(timespec="seconds")
    return stats


def _connect(cfg):
    if cfg["use_ssl"]:
        conn = imaplib.IMAP4_SSL(cfg["host"], int(cfg["port"]))
    else:
        conn = imaplib.IMAP4(cfg["host"], int(cfg["port"]))
    conn.login(cfg["user"], cfg["password"])
    return conn


def _imap_date(days_ago):
    """生成 IMAP 协议要求的日期格式（固定英文月份，避免受系统 locale 影响）"""
    d = datetime.now() - timedelta(days=max(0, int(days_ago)))
    return f"{d.day:02d}-{_MONTHS[d.month - 1]}-{d.year}"


def _search_uids(conn, days):
    typ, data = conn.uid("SEARCH", None, f'(SINCE "{_imap_date(days)}")')
    if typ != "OK" or not data or not data[0]:
        return []
    return data[0].split()


def _decode(value):
    """解码 RFC2047 编码的邮件头（中文主题/文件名常见）"""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value))).strip()
    except Exception:
        return str(value).strip()


def _process_message(conn, uid, stats):
    typ, data = conn.uid("FETCH", uid, "(RFC822)")
    if typ != "OK":
        return
    raw = next((item[1] for item in data if isinstance(item, tuple)), None)
    if not raw:
        return
    msg = email.message_from_bytes(raw)

    subject = _decode(msg.get("Subject"))
    from_name, from_addr = parseaddr(_decode(msg.get("From")))
    sender = f"{from_name} <{from_addr}>" if from_addr else from_name
    message_id = _message_key(msg, uid)

    attachments = _attachments(msg)
    if not attachments:
        stats["no_attachment"] += 1
        insert_email_log(message_id, "", subject, sender, "no_attachment",
                         "邮件中未发现 PDF/DOCX 附件")
        return

    for filename, content in attachments:
        suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if suffix not in SUPPORTED_SUFFIXES:
            stats["unsupported"] += 1
            insert_email_log(message_id, filename, subject, sender, "unsupported",
                             f"不支持的文件类型：{suffix or '未知'}")
            continue
        if email_log_exists(message_id, filename):
            stats["skipped"] += 1
            continue

        text = extract_resume_text(content, filename)
        if not text:
            stats["failed"] += 1
            insert_email_log(message_id, filename, subject, sender, "failed",
                             "无法解析简历文本（可能是扫描件或加密文件）")
            continue

        contact = extract_contact(text)
        exists = find_candidate_by_contact(contact["phone"], contact["email"])
        if exists:
            stats["duplicate"] += 1
            insert_email_log(message_id, filename, subject, sender, "duplicate",
                             f"手机号/邮箱已存在候选人 id={exists['id']}", exists["id"])
            continue

        cid = insert_candidate(
            name=_guess_name(filename, from_name),
            expected_position="",
            skills=text[:200],          # 与上传接口保持一致：正文前 200 字作为预览
            phone=contact["phone"],
            email=contact["email"],
            resume_text=text,
        )
        stats["ingested"] += 1
        insert_email_log(message_id, filename, subject, sender, "ingested",
                         "已入库", cid)
        logger.info("邮箱简历入库：id=%s 姓名=%s 文件=%s", cid, _guess_name(filename, from_name), filename)


def _message_key(msg, uid):
    """邮件唯一标识：优先 Message-ID，缺失时用 uid + 摘要兜底"""
    mid = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
    if mid:
        return mid[:255]
    digest = hashlib.md5(
        f"{msg.get('Subject')}{msg.get('From')}{msg.get('Date')}".encode("utf-8", "ignore")
    ).hexdigest()
    return f"uid-{uid.decode() if isinstance(uid, bytes) else uid}-{digest}"


def _attachments(msg):
    """抽取邮件中的 PDF/DOCX 附件，返回 [(filename, bytes), ...]"""
    found = []
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        filename = _decode(part.get_filename())
        if not filename:
            # 部分平台把简历作为内联附件发送，没有文件名，用 MIME 类型兜底
            ctype = (part.get_content_type() or "").lower()
            ext = {
                "application/pdf": ".pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            }.get(ctype)
            if not ext:
                continue
            filename = f"简历附件{ext}"
        found.append((filename, payload))
    return found


_NAME_NOISE = ("个人简历", "简历", "resume", "cv", "应聘", "求职", "附件")


def _guess_name(filename, from_name):
    """从附件名猜姓名：优先取文件名里的 2~4 个连续中文字段，其次发件人昵称"""
    stem = re.sub(r"\.[^.]+$", "", filename or "")
    stem = re.sub(r"[（(].*?[）)]", "", stem)  # 去掉 (1)、(最新) 之类后缀
    for token in re.split(r"[-_—\s.]+", stem):
        token = re.sub(r"\d+", "", token).strip()
        token = token.lower().replace(" ", "")
        if not token or token in _NAME_NOISE:
            continue
        if re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", token):
            return token
    if from_name and re.fullmatch(r"[\u4e00-\u9fa5]{2,4}", from_name.strip()):
        return from_name.strip()
    return "邮箱投递"


def _scheduler_loop():
    """后台轮询：启动后先同步一次，之后按配置的间隔循环"""
    while True:
        try:
            cfg = load_settings()
            if is_configured(cfg) and cfg["poll_interval"] > 0:
                result = run_ingest(cfg)
                if result["ingested"]:
                    logger.info("定时邮箱同步完成：新增 %s 份简历", result["ingested"])
        except EmailNotConfigured:
            pass
        except Exception:
            logger.exception("定时邮箱同步失败")
        interval = max(10, load_settings()["poll_interval"] or 60)
        if _stop_event.wait(interval):
            return


def start_scheduler():
    """启动后台轮询（未配置或间隔为 0 时不启动）"""
    global _scheduler_thread
    cfg = load_settings()
    if not is_configured(cfg):
        logger.info("邮箱未绑定，可在页面「邮箱配置」中绑定后自动同步")
        return
    if cfg["poll_interval"] <= 0:
        logger.info("同步间隔为 0，仅支持手动触发邮箱同步")
        return
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop, name="imap-ingest", daemon=True
    )
    _scheduler_thread.start()
    logger.info("邮箱收件轮询已启动，间隔 %s 秒", cfg["poll_interval"])


def stop_scheduler():
    """停止后台轮询（进程退出或配置变更时调用）"""
    _stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=5)


def restart_scheduler():
    """配置变更后重启轮询，让新参数立即生效"""
    stop_scheduler()
    start_scheduler()
