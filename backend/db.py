"""MySQL 数据访问层：SQLAlchemy 连接池 + 建库建表 + 种子数据 + 查询封装"""
import hashlib
import logging
import re
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB

logger = logging.getLogger(__name__)

# 候选人招聘流程状态（对应前端看板的列）
CANDIDATE_STATUSES = ("new", "screening", "interview", "offered", "rejected")

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
                password_hash VARCHAR(128) NOT NULL
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

    _ensure_fulltext_index()
    _ensure_status_column()
    seed_users()
    seed_candidates()


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


def seed_users():
    """默认登录账号（密码存 sha256 哈希），按用户名幂等写入"""
    default_users = [
        ("admin", "123456"),
        ("hukun", "12345678"),
    ]
    with _engine.begin() as conn:
        for username, password in default_users:
            exists = conn.execute(
                text("SELECT id FROM users WHERE username=:u"), {"u": username}
            ).first()
            if exists is None:
                h = hashlib.sha256(password.encode()).hexdigest()
                conn.execute(
                    text("INSERT INTO users (username, password_hash) VALUES (:u, :h)"),
                    {"u": username, "h": h},
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
    """校验用户名与密码哈希，返回是否通过"""
    row = _fetch_one(
        "SELECT password_hash FROM users WHERE username=:u", {"u": username}
    )
    return row is not None and row["password_hash"] == password_hash


def list_candidates():
    return _fetch("SELECT * FROM candidates ORDER BY id")


def _extract_years(experience):
    """从经验文本中提取首个数字作为工作年限（如 "3 年前端" -> 3），无则 0"""
    m = re.search(r"\d+", experience or "")
    return int(m.group(0)) if m else 0


def filter_candidates(position=None, skills=None, education=None, min_years=None):
    """结构化筛选候选人：岗位/技能/学历用 LIKE 关键词，年限用数字比较"""
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


def update_candidate_status(candidate_id, status):
    """更新候选人招聘流程状态；非法状态抛 ValueError"""
    if status not in CANDIDATE_STATUSES:
        raise ValueError(f"无效状态：{status}，可选 {list(CANDIDATE_STATUSES)}")
    _execute(
        "UPDATE candidates SET status=:s WHERE id=:cid",
        {"s": status, "cid": candidate_id},
    )


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