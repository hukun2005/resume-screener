"""MySQL 数据访问层：SQLAlchemy 连接池 + 建库建表 + 种子数据 + 查询封装"""
import hashlib
import logging
import re
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
from permissions import (
    ADMIN_ONLY_PERMISSIONS,
    DEFAULT_ROLE_PERMISSIONS,
    FINAL_STATUSES,
    ROLES,
    STATUS_KEYS,
)

logger = logging.getLogger(__name__)

# 候选人招聘流程状态（与 permissions.STATUSES 保持一致，对应前端看板的列）
CANDIDATE_STATUSES = STATUS_KEYS

# 终态：进入「已通过 / 未通过」后保留该天数，到期自动清理档案
RETENTION_DAYS = 7

# 连接池引擎：复用连接、避免每次请求重新握手（解决高并发下连接开销过大的问题）
_engine = create_engine(
    f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4",
    pool_pre_ping=True,   # 取连接前先 ping，自动剔除失效连接
    pool_recycle=1800,    # 连接复用上限 30 分钟，防止 MySQL wait_timeout 断连
    pool_size=5,          # 常驻连接数
    max_overflow=10,      # 峰值可额外借出的连接数
    echo=False,
)


def _fetch(sql, params=None):
    """执行查询，返回 list[dict]"""
    with _engine.connect() as conn:
        rows = conn.execute(text(sql), params or {}).mappings().all()
    return [dict(r) for r in rows]


def _fetch_one(sql, params=None):
    """执行查询，返回单行 dict（无结果返回 None）"""
    with _engine.connect() as conn:
        row = conn.execute(text(sql), params or {}).mappings().first()
    return dict(row) if row is not None else None


def _scalar(sql, params=None):
    """执行查询，返回第一行第一列"""
    with _engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


def _execute(sql, params=None):
    """执行写操作并返回 lastrowid"""
    with _engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.lastrowid


def init_db():
    """建库、建表、写入种子数据（幂等，可重复执行）"""
    # 1) 建库：需使用不带 database 的连接
    base_url = (
        f"mysql+pymysql://{quote_plus(MYSQL_USER)}:{quote_plus(MYSQL_PASSWORD)}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}"
    )
    scratch = create_engine(base_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    with scratch.connect() as conn:
        conn.execute(text(
            f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} DEFAULT CHARACTER SET utf8mb4"
        ))
    scratch.dispose()

    # 2) 建表
    with _engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(128) NOT NULL,
                display_name VARCHAR(50) NOT NULL DEFAULT '',
                role VARCHAR(20) NOT NULL DEFAULT 'hr',
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(50) NOT NULL,
                expected_position VARCHAR(100),
                skills VARCHAR(500),
                experience VARCHAR(500),
                education VARCHAR(200),
                phone VARCHAR(30),
                email VARCHAR(100),
                resume_text TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'new',
                status_changed_at DATETIME NULL,
                status_changed_by VARCHAR(50) NULL,
                interview_at DATETIME NULL,
                interview_mode VARCHAR(20) NULL,
                interviewer VARCHAR(50) NULL,
                interview_feedback TEXT,
                FULLTEXT KEY idx_resume_fulltext (resume_text) WITH PARSER ngram
            )
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS recommendations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                candidate_id INT NOT NULL,
                candidate_name VARCHAR(50),
                requirement VARCHAR(200),
                match_score INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ))
        # 邮箱收件处理日志：同一封邮件的同一个附件只处理一次（幂等去重）
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS email_ingest_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id VARCHAR(255) NOT NULL,
                filename VARCHAR(255) NOT NULL DEFAULT '',
                subject VARCHAR(500),
                sender VARCHAR(255),
                status VARCHAR(20) NOT NULL,
                detail VARCHAR(500),
                candidate_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uk_message_file (message_id, filename)
            )
            """
        ))
        # 邮箱绑定配置：只有一行（id=1），页面保存后覆盖 .env 的默认值
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS email_config (
                id INT PRIMARY KEY,
                host VARCHAR(100) NOT NULL DEFAULT '',
                port INT NOT NULL DEFAULT 993,
                imap_user VARCHAR(100) NOT NULL DEFAULT '',
                password VARCHAR(200) NOT NULL DEFAULT '',
                mailbox VARCHAR(100) NOT NULL DEFAULT 'INBOX',
                use_ssl TINYINT(1) NOT NULL DEFAULT 1,
                search_days INT NOT NULL DEFAULT 7,
                max_per_run INT NOT NULL DEFAULT 50,
                poll_interval INT NOT NULL DEFAULT 300,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """
        ))

        # 角色权限：非管理员角色的授权项，只存已授权的 key
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS role_permissions (
                role VARCHAR(20) NOT NULL,
                perm VARCHAR(50) NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                PRIMARY KEY (role, perm)
            )
            """
        ))

        # 账号与权限管理界面的操作日志（谁在什么时候改了什么）
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                actor VARCHAR(50) NOT NULL,
                actor_name VARCHAR(50) NOT NULL DEFAULT '',
                actor_role VARCHAR(20) NOT NULL DEFAULT '',
                action VARCHAR(30) NOT NULL,
                target VARCHAR(150) NOT NULL DEFAULT '',
                detail TEXT,
                ip VARCHAR(60) NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                KEY idx_audit_action (action),
                KEY idx_audit_created (created_at)
            )
            """
        ))

    _ensure_fulltext_index()
    _ensure_status_column()
    _ensure_status_changed_column()
    _ensure_users_columns()
    _ensure_status_changed_by_column()
    _ensure_interview_columns()
    seed_users()
    seed_candidates()
    seed_role_permissions()


def _ensure_fulltext_index():
    """为已存在但缺索引的 candidates 表补建全文索引（幂等）"""
    try:
        c = _scalar(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE table_schema=:db AND table_name='candidates' "
            "AND index_name='idx_resume_fulltext'",
            {"db": MYSQL_DB},
        )
        if not c:
            with _engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE candidates "
                    "ADD FULLTEXT INDEX idx_resume_fulltext (resume_text) WITH PARSER ngram"
                ))
    except Exception:
        logger.exception("补建全文索引失败（不影响主流程）")


def _ensure_status_column():
    """为已存在的 candidates 表补建 status 列（幂等迁移，兼容旧库）"""
    try:
        c = _scalar(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE table_schema=:db AND table_name='candidates' AND column_name='status'",
            {"db": MYSQL_DB},
        )
        if not c:
            with _engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE candidates ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'new'"
                ))
    except Exception:
        logger.exception("补建 status 列失败（不影响主流程）")


def _ensure_status_changed_column():
    """为已存在的 candidates 表补建 status_changed_at 列（幂等迁移）

    已处于终态的历史数据以本次迁移时间为起点开始计时，避免升级后立即被清理。
    """
    try:
        c = _scalar(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE table_schema=:db AND table_name='candidates' "
            "AND column_name='status_changed_at'",
            {"db": MYSQL_DB},
        )
        if not c:
            with _engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE candidates ADD COLUMN status_changed_at DATETIME NULL"
                ))
                conn.execute(text(
                    "UPDATE candidates SET status_changed_at=NOW() "
                    "WHERE status IN ('offered','rejected') AND status_changed_at IS NULL"
                ))
    except Exception:
        logger.exception("补建 status_changed_at 列失败（不影响主流程）")


def _ensure_users_columns():
    """为已存在的 users 表补建角色相关列（幂等迁移）

    历史账号统一提升为管理员，避免升级后失去管理入口。
    """
    try:
        cols = {
            "display_name": "ALTER TABLE users ADD COLUMN display_name VARCHAR(50) NOT NULL DEFAULT ''",
            "role": "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'hr'",
            "is_active": "ALTER TABLE users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1",
            "created_at": "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }
        for name, ddl in cols.items():
            exists = _scalar(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE table_schema=:db AND table_name='users' AND column_name=:col",
                {"db": MYSQL_DB, "col": name},
            )
            if not exists:
                with _engine.begin() as conn:
                    conn.execute(text(ddl))
                if name == "role":
                    # 升级前就存在的账号没有角色概念，视为管理员
                    with _engine.begin() as conn:
                        conn.execute(text("UPDATE users SET role='admin'"))
    except Exception:
        logger.exception("补建 users 角色列失败（不影响主流程）")


def _ensure_status_changed_by_column():
    """为 candidates 表补建 status_changed_by 列（幂等迁移，记录是谁推进的阶段）"""
    try:
        c = _scalar(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE table_schema=:db AND table_name='candidates' "
            "AND column_name='status_changed_by'",
            {"db": MYSQL_DB},
        )
        if not c:
            with _engine.begin() as conn:
                conn.execute(text(
                    "ALTER TABLE candidates ADD COLUMN status_changed_by VARCHAR(50) NULL"
                ))
    except Exception:
        logger.exception("补建 status_changed_by 列失败（不影响主流程）")


def _ensure_interview_columns():
    """为 candidates 表补建面试安排相关列（幂等迁移）"""
    columns = {
        "interview_at": "DATETIME NULL",
        "interview_mode": "VARCHAR(20) NULL",
        "interviewer": "VARCHAR(50) NULL",
        "interview_feedback": "TEXT",
    }
    try:
        for name, ddl in columns.items():
            c = _scalar(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE table_schema=:db AND table_name='candidates' "
                "AND column_name=:col",
                {"db": MYSQL_DB, "col": name},
            )
            if not c:
                with _engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE candidates ADD COLUMN {name} {ddl}"))
    except Exception:
        logger.exception("补建面试安排列失败（不影响主流程）")


def seed_users():
    """默认登录账号（密码存 sha256 哈希），按用户名幂等写入"""
    default_users = [
        ("admin", "123456", "系统管理员", "admin"),
        ("hukun", "12345678", "招聘负责人", "admin"),
        ("hr1", "123456", "HR 张敏", "hr"),
        ("tech1", "123456", "技术面试官 李工", "tech"),
    ]
    with _engine.begin() as conn:
        for username, password, display_name, role in default_users:
            exists = conn.execute(
                text("SELECT id FROM users WHERE username=:u"), {"u": username}
            ).first()
            if exists is None:
                h = hashlib.sha256(password.encode()).hexdigest()
                conn.execute(
                    text(
                        "INSERT INTO users (username, password_hash, display_name, role) "
                        "VALUES (:u, :h, :d, :r)"
                    ),
                    {"u": username, "h": h, "d": display_name, "r": role},
                )


def seed_role_permissions():
    """首次初始化角色权限：表为空时按默认配置写入"""
    try:
        if _scalar("SELECT COUNT(*) FROM role_permissions"):
            return
        for role, keys in DEFAULT_ROLE_PERMISSIONS.items():
            for key in keys:
                _execute(
                    "INSERT IGNORE INTO role_permissions (role, perm) VALUES (:r, :p)",
                    {"r": role, "p": key},
                )
    except Exception:
        logger.exception("初始化角色权限失败（不影响主流程）")


def get_role_permissions():
    """返回 {role: set(权限 key)}，管理员的权限不在此表中"""
    rows = _fetch("SELECT role, perm FROM role_permissions")
    result = {r: set() for r in ROLES if r != "admin"}
    for row in rows:
        result.setdefault(row["role"], set()).add(row["perm"])
    return result


def set_role_permissions(role, keys):
    """覆盖写入某角色的权限（管理员固定全部，不可修改）"""
    if role == "admin":
        raise ValueError("管理员的权限固定为全部，不能修改")
    keys = [k for k in keys if k not in ADMIN_ONLY_PERMISSIONS]
    with _engine.begin() as conn:
        conn.execute(text("DELETE FROM role_permissions WHERE role=:r"), {"r": role})
        for key in keys:
            conn.execute(
                text("INSERT IGNORE INTO role_permissions (role, perm) VALUES (:r, :p)"),
                {"r": role, "p": key},
            )


def seed_candidates():
    """示例简历数据（10 条，覆盖常见岗位），表为空时才写入"""
    rows = [
        ("张三", "前端开发工程师", "Vue,React,TypeScript,JavaScript",
         "3 年前端开发，主导电商中台与可视化大屏", "本科·计算机",
         "13800000001", "zhangsan@example.com",
         "张三，3 年前端开发经验，熟练 Vue、React、TypeScript，主导电商中台与三维可视化大屏项目。"),
        ("李四", "后端开发工程师", "Python,FastAPI,MySQL,Redis",
         "4 年后端，负责订单系统与高并发接口", "本科·软件工程",
         "13800000002", "lisi@example.com",
         "李四，4 年后端经验，精通 Python/FastAPI、MySQL、Redis，负责订单系统与高并发接口开发。"),
        ("王五", "Python 开发工程师", "Python,LangChain,RAG,SQL",
         "2 年，独立完成 RAG 知识库与智能问答", "本科·计算机",
         "13800000003", "wangwu@example.com",
         "王五，2 年 Python 开发，独立落地 RAG 知识库、智能问答系统，熟悉大模型 API 调用。"),
        ("赵六", "前端开发工程师", "Vue,TypeScript,小程序",
         "2 年，H5 与微信小程序开发", "本科·计算机",
         "13800000004", "zhaoliu@example.com",
         "赵六，2 年前端开发，熟悉 Vue、TypeScript 与微信小程序开发。"),
        ("孙七", "数据分析师", "Python,SQL,Excel,Tableau",
         "3 年数据报表与业务分析", "本科·统计学",
         "13800000005", "sunqi@example.com",
         "孙七，3 年数据分析经验，熟悉 Python、SQL、Excel、Tableau，负责业务报表与用户增长分析。"),
        ("周八", "Java 后端工程师", "Java,SpringBoot,MySQL",
         "5 年交易系统与微服务", "本科·软件工程",
         "13800000006", "zhouba@example.com",
         "周八，5 年 Java 后端经验，精通 SpringBoot、MySQL，负责交易系统与微服务架构。"),
        ("吴九", "测试工程师", "Python,自动化测试,Selenium",
         "3 年接口自动化与性能测试", "本科·计算机",
         "13800000007", "wujiu@example.com",
         "吴九，3 年测试经验，熟悉 Python 自动化测试、Selenium 与接口测试。"),
        ("郑十", "产品经理", "Axure,原型,需求分析",
         "4 年 B 端产品设计", "本科·信息管理",
         "13800000008", "zhengshi@example.com",
         "郑十，4 年 B 端产品经理，擅长需求分析、原型设计与项目管理。"),
        ("钱一", "全栈开发工程师", "React,Node.js,Python,TypeScript",
         "3 年全栈，前后端一体化交付", "本科·计算机",
         "13800000009", "qianyi@example.com",
         "钱一，3 年全栈开发，熟悉 React、Node.js、Python、TypeScript，前后端一体化交付。"),
        ("陈二", "AI 算法工程师", "Python,PyTorch,深度学习,NLP",
         "3 年 NLP 与推荐算法", "硕士·人工智能",
         "13800000010", "chener@example.com",
         "陈二，3 年 AI 算法经验，精通 Python、PyTorch、深度学习与 NLP，负责推荐与文本理解。"),
    ]
    with _engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM candidates")).scalar()
        if count == 0:
            for name, pos, skills, exp, edu, phone, email, resume_text in rows:
                conn.execute(text(
                    """
                    INSERT INTO candidates
                    (name, expected_position, skills, experience, education, phone, email, resume_text)
                    VALUES (:name,:pos,:skills,:exp,:edu,:phone,:email,:text)
                    """
                ), {
                    "name": name, "pos": pos, "skills": skills, "exp": exp,
                    "edu": edu, "phone": phone, "email": email, "text": resume_text,
                })


def verify_user(username, password_hash):
    """校验用户名与密码哈希，通过则返回账号信息（含角色），否则返回 None"""
    row = _fetch_one(
        "SELECT id, username, password_hash, display_name, role, is_active "
        "FROM users WHERE username=:u",
        {"u": username},
    )
    if row is None or row["password_hash"] != password_hash:
        return None
    if not row["is_active"]:
        return None
    return row


def list_users():
    """账号列表（不含密码哈希）"""
    return _fetch(
        "SELECT id, username, display_name, role, is_active, created_at "
        "FROM users ORDER BY id"
    )


def get_user(user_id):
    return _fetch_one(
        "SELECT id, username, display_name, role, is_active, created_at "
        "FROM users WHERE id=:id",
        {"id": user_id},
    )


def create_user(username, password_hash, display_name, role):
    """新建账号，用户名重复时抛 ValueError"""
    exists = _fetch_one("SELECT id FROM users WHERE username=:u", {"u": username})
    if exists:
        raise ValueError(f"账号 {username} 已存在")
    _execute(
        "INSERT INTO users (username, password_hash, display_name, role) "
        "VALUES (:u, :h, :d, :r)",
        {"u": username, "h": password_hash, "d": display_name or username, "r": role},
    )
    return _fetch_one("SELECT * FROM users WHERE username=:u", {"u": username})


def update_user(user_id, role=None, is_active=None, password_hash=None, display_name=None):
    """按需更新账号字段（角色 / 启用状态 / 密码 / 姓名）"""
    sets, params = [], {"id": user_id}
    if role is not None:
        sets.append("role=:role")
        params["role"] = role
    if is_active is not None:
        sets.append("is_active=:active")
        params["active"] = 1 if is_active else 0
    if password_hash is not None:
        sets.append("password_hash=:pwd")
        params["pwd"] = password_hash
    if display_name is not None:
        sets.append("display_name=:dn")
        params["dn"] = display_name
    if not sets:
        return get_user(user_id)
    _execute(f"UPDATE users SET {', '.join(sets)} WHERE id=:id", params)
    return get_user(user_id)


def count_active_admins(exclude_user_id=None):
    """当前启用的管理员数量（用于防止把最后一个管理员降级/停用）"""
    sql = "SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1"
    params = None
    if exclude_user_id is not None:
        sql += " AND id<>:id"
        params = {"id": exclude_user_id}
    return _scalar(sql, params)


def list_candidates():
    return _fetch("SELECT * FROM candidates ORDER BY id")


def _extract_years(experience):
    """从经验文本中提取首个数字作为工作年限（如 "3 年前端" -> 3），无则 0"""
    m = re.search(r"\d+", experience or "")
    return int(m.group(0)) if m else 0


def filter_candidates(position=None, skills=None, education=None, min_years=None,
                      statuses=None):
    """结构化筛选候选人：岗位/技能/学历用 LIKE 关键词，年限用数字比较

    statuses 用于按角色限定可见范围（如技术部只看已推送的候选人）。
    """
    conds = []
    params = {}
    if position:
        conds.append("expected_position LIKE :pos")
        params["pos"] = f"%{position}%"
    if skills:
        conds.append("skills LIKE :skills")
        params["skills"] = f"%{skills}%"
    if education:
        conds.append("education LIKE :edu")
        params["edu"] = f"%{education}%"
    if statuses:
        keys = [f"st{i}" for i in range(len(statuses))]
        conds.append("status IN (" + ", ".join(":" + k for k in keys) + ")")
        for k, v in zip(keys, statuses):
            params[k] = v

    sql = "SELECT * FROM candidates"
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY id"
    rows = _fetch(sql, params)

    if min_years is not None and min_years > 0:
        rows = [r for r in rows if _extract_years(r.get("experience")) >= min_years]
    return rows


def get_candidate(candidate_id):
    return _fetch_one("SELECT * FROM candidates WHERE id=:cid", {"cid": candidate_id})


def update_candidate_status(candidate_id, status, by_username=None):
    """更新候选人招聘流程状态；非法状态抛 ValueError

    进入终态（offered/rejected）时记录计时起点 status_changed_at，用于到期自动清理；
    从终态退回流程中时清空计时，避免被误删。by_username 记录是谁推进的阶段。
    """
    if status not in CANDIDATE_STATUSES:
        raise ValueError(f"无效状态：{status}，可选 {list(CANDIDATE_STATUSES)}")
    current = get_candidate(candidate_id)
    if current is None:
        return
    if status in FINAL_STATUSES:
        # 同一终态重复提交不重置倒计时；终态之间互转则重新计时
        sql = (
            "UPDATE candidates SET status=:s WHERE id=:cid"
            if current["status"] == status
            else "UPDATE candidates SET status=:s, status_changed_at=NOW() WHERE id=:cid"
        )
    else:
        sql = "UPDATE candidates SET status=:s, status_changed_at=NULL WHERE id=:cid"
    _execute(sql, {"s": status, "cid": candidate_id})
    if by_username:
        _execute(
            "UPDATE candidates SET status_changed_by=:by WHERE id=:cid",
            {"by": by_username, "cid": candidate_id},
        )


def update_interview(candidate_id, interview_at, interview_mode, interviewer, feedback):
    """保存面试安排与反馈；空字符串统一存为 NULL"""
    _execute(
        "UPDATE candidates SET interview_at=:at, interview_mode=:mode, "
        "interviewer=:who, interview_feedback=:fb WHERE id=:cid",
        {
            "at": interview_at,
            "mode": interview_mode or None,
            "who": interviewer or None,
            "fb": feedback or None,
            "cid": candidate_id,
        },
    )
    return get_candidate(candidate_id)


def purge_expired_candidates(days=RETENTION_DAYS):
    """清理进入终态超过 days 天的候选人，返回被删除的 id 列表"""
    rows = _fetch(
        """
        SELECT id FROM candidates
        WHERE status IN ('offered','rejected')
          AND status_changed_at IS NOT NULL
          AND status_changed_at <= DATE_SUB(NOW(), INTERVAL :days DAY)
        """,
        {"days": int(days)},
    )
    ids = [r["id"] for r in rows]
    for cid in ids:
        delete_candidate(cid)
    if ids:
        logger.info("已自动清理 %s 位终态候选人：%s", len(ids), ids)
    return ids


def update_candidate(candidate_id, name, expected_position="", skills="",
                     experience="", education="", phone="", email=""):
    """更新候选人结构化信息（姓名/岗位/技能/经历/学历/联系方式，不含简历正文）"""
    _execute(
        """
        UPDATE candidates
        SET name=:name, expected_position=:pos, skills=:skills, experience=:exp,
            education=:edu, phone=:phone, email=:email
        WHERE id=:cid
        """,
        {
            "name": name, "pos": expected_position, "skills": skills, "exp": experience,
            "edu": education, "phone": phone, "email": email, "cid": candidate_id,
        },
    )
    return get_candidate(candidate_id)


def delete_candidate(candidate_id):
    """删除候选人及其关联的推荐记录"""
    _execute("DELETE FROM recommendations WHERE candidate_id=:cid", {"cid": candidate_id})
    _execute("DELETE FROM candidates WHERE id=:cid", {"cid": candidate_id})


def get_candidates_by_ids(ids):
    """按 id 列表批量查询候选人，返回 list[dict]（保持输入顺序不保证，调用方自行 map）"""
    if not ids:
        return []
    keys = [f"id{i}" for i in range(len(ids))]
    params = {keys[i]: ids[i] for i in range(len(ids))}
    sql = f"SELECT * FROM candidates WHERE id IN ({', '.join(':' + k for k in keys)})"
    return _fetch(sql, params)


def insert_candidate(name, expected_position="", skills="", experience="",
                     education="", phone="", email="", resume_text=""):
    """新增一条候选人简历，返回新记录的 id"""
    return _execute(
        """
        INSERT INTO candidates
        (name, expected_position, skills, experience, education, phone, email, resume_text)
        VALUES (:name,:pos,:skills,:exp,:edu,:phone,:email,:text)
        """,
        {
            "name": name, "pos": expected_position, "skills": skills, "exp": experience,
            "edu": education, "phone": phone, "email": email, "text": resume_text,
        },
    )


def add_recommendation(candidate_id, candidate_name, requirement, match_score):
    """写入一条推荐记录"""
    _execute(
        """
        INSERT INTO recommendations (candidate_id, candidate_name, requirement, match_score)
        VALUES (:cid,:name,:req,:score)
        """,
        {
            "cid": candidate_id, "name": candidate_name,
            "req": requirement, "score": match_score,
        },
    )


def list_recommendations():
    return _fetch("SELECT * FROM recommendations ORDER BY id DESC LIMIT 20")


def find_candidate_by_contact(phone="", email=""):
    """按手机号或邮箱查重，命中任意一项即视为同一候选人（邮箱忽略大小写）"""
    conds = []
    params = {}
    if phone:
        conds.append("phone=:phone")
        params["phone"] = phone
    if email:
        conds.append("LOWER(email)=LOWER(:email)")
        params["email"] = email
    if not conds:
        return None
    return _fetch_one(
        "SELECT * FROM candidates WHERE " + " OR ".join(conds) + " LIMIT 1", params
    )


def email_log_exists(message_id, filename=""):
    """判断某封邮件的某个附件是否已处理过（幂等去重）"""
    return bool(_scalar(
        "SELECT COUNT(*) FROM email_ingest_log WHERE message_id=:m AND filename=:f",
        {"m": message_id, "f": filename or ""},
    ))


def insert_email_log(message_id, filename="", subject="", sender="",
                     status="ingested", detail="", candidate_id=None):
    """写入一条邮箱收件处理记录；重复键（并发重复处理）直接忽略"""
    _execute(
        """
        INSERT IGNORE INTO email_ingest_log
        (message_id, filename, subject, sender, status, detail, candidate_id)
        VALUES (:mid, :file, :subj, :sender, :status, :detail, :cid)
        """,
        {
            "mid": message_id[:255], "file": (filename or "")[:255],
            "subj": (subject or "")[:500], "sender": (sender or "")[:255],
            "status": status, "detail": (detail or "")[:500], "cid": candidate_id,
        },
    )


def list_email_logs(limit=20):
    """最近的邮箱收件处理记录（倒序）"""
    return _fetch(
        "SELECT * FROM email_ingest_log ORDER BY id DESC LIMIT :lim", {"lim": int(limit)}
    )


def get_email_config():
    """读取页面保存的邮箱绑定配置（未保存过返回 None）"""
    return _fetch_one("SELECT * FROM email_config WHERE id=1")


def save_email_config(host, port, imap_user, password, mailbox,
                      use_ssl, search_days, max_per_run, poll_interval):
    """保存邮箱绑定配置（单行 upsert），返回读取结果"""
    _execute(
        """
        INSERT INTO email_config
        (id, host, port, imap_user, password, mailbox, use_ssl,
         search_days, max_per_run, poll_interval)
        VALUES (1,:host,:port,:imap_user,:password,:mailbox,:use_ssl,
                :search_days,:max_per_run,:poll_interval)
        ON DUPLICATE KEY UPDATE
            host=VALUES(host), port=VALUES(port), imap_user=VALUES(imap_user),
            password=VALUES(password), mailbox=VALUES(mailbox),
            use_ssl=VALUES(use_ssl), search_days=VALUES(search_days),
            max_per_run=VALUES(max_per_run), poll_interval=VALUES(poll_interval)
        """,
        {
            "host": host, "port": int(port), "imap_user": imap_user,
            "password": password or "", "mailbox": mailbox or "INBOX",
            "use_ssl": 1 if use_ssl else 0, "search_days": int(search_days),
            "max_per_run": int(max_per_run), "poll_interval": int(poll_interval),
        },
    )
    return get_email_config()


def add_audit_log(actor, action, target="", detail="", ip=""):
    """写入一条账号 / 权限管理操作日志；失败不影响主流程"""
    try:
        _execute(
            "INSERT INTO audit_logs "
            "(actor, actor_name, actor_role, action, target, detail, ip) "
            "VALUES (:actor, :name, :role, :action, :target, :detail, :ip)",
            {
                "actor": actor.get("username", ""),
                "name": actor.get("display_name") or actor.get("username", ""),
                "role": actor.get("role", ""),
                "action": action,
                "target": target or "",
                "detail": detail or "",
                "ip": ip or "",
            },
        )
    except Exception:
        logger.exception("写入操作日志失败")


def list_audit_logs(limit=50, action=None, keyword=None):
    """账号与权限管理操作日志（倒序），支持按动作与关键词过滤"""
    where, params = [], {}
    if action:
        where.append("action=:action")
        params["action"] = action
    if keyword:
        where.append(
            "(actor LIKE :kw OR actor_name LIKE :kw OR target LIKE :kw OR detail LIKE :kw)"
        )
        params["kw"] = f"%{keyword}%"
    sql = (
        "SELECT id, actor, actor_name, actor_role, action, target, detail, ip, created_at "
        "FROM audit_logs"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT :lim"
    params["lim"] = max(1, min(int(limit), 500))
    return _fetch(sql, params)