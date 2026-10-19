"""AI Agent 可调用的工具：简历语义检索与推荐（LangChain @tool 声明）"""
import threading

from langchain_core.tools import tool

from db import get_conn
from embedding import embed, cosine_similarity
import vector_store

# 技能关键词表，用于从自然语言需求中识别技能并与简历匹配（语义检索失败时的回退方案）
SKILL_KEYWORDS = [
    "python", "java", "react", "vue", "typescript", "javascript", "node",
    "fastapi", "springboot", "mysql", "redis", "sql",
    "数据分析", "测试", "产品", "算法", "深度学习", "pytorch", "nlp",
    "小程序", "全栈", "langchain", "rag", "大模型", "前端", "后端",
]

# 候选人向量缓存 {candidate_id: [float...]}，新增/变更简历后自动补齐
_EMB_CACHE = {}
_cache_lock = threading.Lock()


def _candidate_text(row):
    """把一个候选人拼成一段用于向量化的文本"""
    return " ".join(filter(None, [
        row.get("expected_position") or "",
        row.get("skills") or "",
        row.get("resume_text") or "",
    ]))


def _get_candidate_vectors(rows):
    """批量获取候选人的向量（带内存缓存），返回 {id: vector}"""
    result = {}
    pending = []
    for r in rows:
        if r["id"] in _EMB_CACHE:
            result[r["id"]] = _EMB_CACHE[r["id"]]
        else:
            pending.append(r)
    if pending:
        vectors = embed([_candidate_text(r) for r in pending])
        with _cache_lock:
            for r, v in zip(pending, vectors):
                _EMB_CACHE[r["id"]] = v
                result[r["id"]] = v
    return result


def _match_score(row, requirement):
    """按技能关键词命中情况打分（0~100），语义检索不可用时的回退"""
    text = " ".join([
        row.get("skills") or "",
        row.get("expected_position") or "",
        row.get("resume_text") or "",
    ]).lower()
    req = (requirement or "").lower()
    demanded = [kw for kw in SKILL_KEYWORDS if kw.lower() in req]
    if not demanded:
        return 60
    hits = sum(1 for kw in demanded if kw.lower() in text)
    if hits == 0:
        return 0
    return round(60 + (hits / len(demanded)) * 40)


def _semantic_scores(rows, requirement):
    """用向量化 + 余弦相似度打分，返回 {id: score}；失败返回 None"""
    try:
        q_vec = embed([requirement])[0]
        vecs = _get_candidate_vectors(rows)
        return {
            r["id"]: round(max(0.0, cosine_similarity(q_vec, vecs[r["id"]])) * 100)
            for r in rows
        }
    except Exception:
        return None


def _score_single(row, requirement):
    """给单个候选人打分：优先语义，回退关键词"""
    sem = _semantic_scores([row], requirement)
    if sem is not None:
        return sem[row["id"]]
    return _match_score(row, requirement)


def _to_result(row, score):
    return {
        "id": row["id"],
        "name": row["name"],
        "expected_position": row["expected_position"],
        "skills": row["skills"],
        "experience": row["experience"],
        "education": row["education"],
        "match_score": score,
    }


def _fetch_all_candidates():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM candidates")
        rows = cur.fetchall()
    conn.close()
    return rows


@tool
def search_candidates(requirement: str, limit: int = 5) -> list:
    """根据招聘需求描述，从简历库中语义检索匹配度最高的候选人。

    Args:
        requirement: 招聘需求描述，例如目标岗位或要求技能。
        limit: 最多返回人数，默认 5。
    """
    # 优先用 FAISS 向量索引检索（O(log N)），失败或召回为空时回退暴力语义/关键词
    try:
        hits = vector_store.search(requirement, top_k=limit)
    except Exception:
        hits = None

    if hits:
        conn = get_conn()
        with conn.cursor() as cur:
            ids = [h[0] for h in hits]
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(
                f"SELECT * FROM candidates WHERE id IN ({placeholders})", ids
            )
            rows = cur.fetchall()
        conn.close()
        by_id = {r["id"]: r for r in rows}
        results = [_to_result(by_id[cid], score) for cid, score in hits if cid in by_id]
        if results:
            return results

    rows = _fetch_all_candidates()
    if not rows:
        return []

    scores = _semantic_scores(rows, requirement)
    if scores is None:  # 语义检索失败，回退关键词
        scores = {r["id"]: _match_score(r, requirement) for r in rows}

    scored = [(r, scores.get(r["id"], 0)) for r in rows if scores.get(r["id"], 0) > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [_to_result(r, s) for r, s in scored[:limit]]


@tool
def recommend_candidate(candidate_id: int, requirement: str) -> str:
    """把指定候选人推荐给面试官，写入推荐记录。

    Args:
        candidate_id: 候选人 id。
        requirement: 本次招聘需求描述。
    """
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM candidates WHERE id=%s", (candidate_id,))
        c = cur.fetchone()
        if not c:
            conn.close()
            return "未找到该候选人"
        score = _score_single(c, requirement)
        cur.execute(
            """
            INSERT INTO recommendations (candidate_id, candidate_name, requirement, match_score)
            VALUES (%s,%s,%s,%s)
            """,
            (c["id"], c["name"], requirement, score),
        )
    conn.close()
    return f"已将 {c['name']}（匹配度 {score}%）推荐给面试官，可进入简历详情查看"


# LangChain Agent 使用的工具列表
AGENT_TOOLS = [search_candidates, recommend_candidate]