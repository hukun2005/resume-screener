"""MySQL 连接、建表、种子数据与查询封装"""
import hashlib

import pymysql

from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


def get_conn():
    """获取一个 MySQL 连接（自动提交，返回字典行）"""
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )
    conn.autocommit(True)
    return conn


def init_db():
    """建库、建表、写入种子数据（幂等，可重复执行）"""
    # 先不带 database 连接，保证数据库存在
    conn = pymysql.connect(
        host=MYSQL_HOST, port=MYSQL_PORT, user=MYSQL_USER,
        password=MYSQL_PASSWORD, charset="utf8mb4",
    )
    conn.autocommit(True)
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB} DEFAULT CHARACTER SET utf8mb4"
        )
    conn.close()

    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password_hash VARCHAR(128) NOT NULL
            )
            """
        )
        cur.execute(
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
                resume_text TEXT
            )
            """
        )
        cur.execute(
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
        )
    seed_users(conn)
    seed_candidates(conn)
    conn.close()


def seed_users(conn):
    """默认登录账号（密码存 sha256 哈希），按用户名幂等写入"""
    default_users = [
        ("admin", "123456"),
        ("hukun", "12345678"),
    ]
    with conn.cursor() as cur:
        for username, password in default_users:
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            if cur.fetchone() is None:
                h = hashlib.sha256(password.encode()).hexdigest()
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                    (username, h),
                )


def seed_candidates(conn):
    """示例简历数据（10 条，覆盖常见岗位）"""
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
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM candidates")
        if cur.fetchone()["c"] == 0:
            for r in rows:
                cur.execute(
                    """
                    INSERT INTO candidates
                    (name, expected_position, skills, experience, education, phone, email, resume_text)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    r,
                )


def verify_user(username, password_hash):
    """校验用户名与密码哈希，返回是否通过"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT password_hash FROM users WHERE username=%s", (username,)
        )
        row = cur.fetchone()
    conn.close()
    return row is not None and row["password_hash"] == password_hash


def list_candidates():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM candidates ORDER BY id")
        rows = cur.fetchall()
    conn.close()
    return rows


def get_candidate(candidate_id):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM candidates WHERE id=%s", (candidate_id,))
        row = cur.fetchone()
    conn.close()
    return row


def insert_candidate(name, expected_position="", skills="", experience="",
                     education="", phone="", email="", resume_text=""):
    """新增一条候选人简历，返回新记录的 id"""
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidates
            (name, expected_position, skills, experience, education, phone, email, resume_text)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (name, expected_position, skills, experience, education, phone, email, resume_text),
        )
        cid = cur.lastrowid
    conn.close()
    return cid


def list_recommendations():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM recommendations ORDER BY id DESC LIMIT 20")
        rows = cur.fetchall()
    conn.close()
    return rows