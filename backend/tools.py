"""AI Agent 可调用的工具：简历语义检索与推荐（LangChain @tool 声明）"""
import logging
import threading

from langchain_core.tools import tool

from db import add_recommendation, get_candidate, get_candidates_by_ids, list_candidates
from embedding import embed, cosine_similarity
from vector_store import candidate_text
import vector_store

logger = logging.getLogger(__name__)

# 技能关键词表，用于从自然语言需求中识别技能并与简历匹配（语义检索失败时的回退/融合方案）
SKILL_KEYWORDS = [
    "python", "java", "react", "vue", "typescript", "javascript", "node",
    "fastapi", "springboot", "mysql", "redis", "sql",
    "数据分析", "测试", "产品", "算法", "深度学习", "pytorch", "nlp",
    "小程序", "全栈", "langchain", "rag", "大模型", "前端", "后端",
]

# 候选人向量缓存 {candidate_id: [float...]}，新增/变更简历后自动补齐
_EMB_CACHE = {}
_cache_lock = threading.Lock()


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
        vectors = embed([candidate_text(r) for r in pending])
        with _cache_lock:
            for r, v in zip(pending, vectors):
                _EMB_CACHE[r["id"]] = v
                result[r["id"]] = v
    return result


def _demanded_keywords(requirement):
    """从需求描述里识别命中的技能关键词（小写，去重保序）"""
    req = (requirement or "").lower()
    seen = set()
    out = []
    for kw in SKILL_KEYWORDS:
        k = kw.lower()
        if k in req and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _candidate_fields_text(row):
    """拼接候选人的可匹配字段（技能+岗位+正文），用于关键词命中判断"""
    return " ".join([
        row.get("skills") or "",
        row.get("expected_position") or "",
        row.get("resume_text") or "",
    ])


def _keyword_score(row, demanded):
    """基于技能关键词命中比例打分（0~100）；无明确需求词时返回中性 50"""
    if not demanded:
        return 50
    text = _candidate_fields_text(row).lower()
    hits = sum(1 for kw in demanded if kw in text)
    if hits == 0:
        return 0
    return round((hits / len(demanded)) * 100)


def _match_score(row, requirement):
    """关键词打分（兼容旧逻辑入口）"""
    return _keyword_score(row, _demanded_keywords(requirement))


def _semantic_scores(rows, requirement):
    """用向量化 + 余弦相似度打分，返回 {id: score}；失败返回 None 并记录日志"""
    try:
        q_vec = embed([requirement])[0]
        vecs = _get_candidate_vectors(rows)
        return {
            r["id"]: round(max(0.0, cosine_similarity(q_vec, vecs[r["id"]])) * 100)
            for r in rows
        }
    except Exception:
        logger.exception("语义检索失败，回退关键词打分")
        return None


def _hybrid_scores(rows, requirement):
    """语义 + 关键词混合打分：语义为主（0.6）、关键词为辅（0.4）加权融合"""
    sem = _semantic_scores(rows, requirement)
    demanded = _demanded_keywords(requirement)
    if sem is None:
        return {r["id"]: _keyword_score(r, demanded) for r in rows}
    if not demanded:
        return sem  # 无技能关键词时退化为纯语义，避免中性分干扰排序
    return {
        r["id"]: round(0.6 * sem[r["id"]] + 0.4 * _keyword_score(r, demanded))
        for r in rows
    }


def _score_single(row, requirement):
    """给单个候选人打分（混合）"""
    return _hybrid_scores([row], requirement).get(row["id"], 0)


def _match_reason(row, demanded):
    """生成推荐理由：命中了哪些技能关键词、候选人的意向岗位"""
    text = _candidate_fields_text(row).lower()
    hits = [kw for kw in demanded if kw in text]
    parts = []
    if hits:
        parts.append("命中技能：" + "、".join(hits))
    if row.get("expected_position"):
        parts.append("意向岗位：" + row["expected_position"])
    if not parts:
        parts.append("语义综合匹配")
    return "；".join(parts)


def _to_result(row, score, demanded):
    return {
        "id": row["id"],
        "name": row["name"],
        "expected_position": row["expected_position"],
        "skills": row["skills"],
        "experience": row["experience"],
        "education": row["education"],
        "match_score": score,
        "matched_skills": [kw for kw in demanded if kw in _candidate_fields_text(row).lower()],
        "match_reason": _match_reason(row, demanded),
    }


@tool
def search_candidates(requirement: str, limit: int = 5) -> list:
    """根据招聘需求描述，从简历库中语义检索匹配度最高的候选人。

    Args:
        requirement: 招聘需求描述，例如目标岗位或要求技能。
        limit: 最多返回人数，默认 5。
    """
    demanded = _demanded_keywords(requirement)
    # 优先用 FAISS 向量索引检索（O(log N)），失败或召回为空时回退混合检索
    try:
        hits = vector_store.search(requirement, top_k=limit)
    except Exception:
        logger.exception("FAISS 检索失败，回退全量混合检索")
        hits = None

    if hits:
        ids = [h[0] for h in hits]
        rows = get_candidates_by_ids(ids)
        by_id = {r["id"]: r for r in rows}
        results = [_to_result(by_id[cid], score, demanded) for cid, score in hits if cid in by_id]
        if results:
            return results

    rows = list_candidates()
    if not rows:
        return []

    scores = _hybrid_scores(rows, requirement)
    scored = [(r, scores.get(r["id"], 0)) for r in rows if scores.get(r["id"], 0) > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [_to_result(r, s, demanded) for r, s in scored[:limit]]


@tool
def recommend_candidate(candidate_id: int, requirement: str) -> str:
    """把指定候选人推荐给面试官，写入推荐记录。

    Args:
        candidate_id: 候选人 id。
        requirement: 本次招聘需求描述。
    """
    c = get_candidate(candidate_id)
    if not c:
        return "未找到该候选人"
    score = _score_single(c, requirement)
    add_recommendation(c["id"], c["name"], requirement, score)
    return f"已将 {c['name']}（匹配度 {score}%）推荐给面试官，可进入简历详情查看"


# LangChain Agent 使用的工具列表
AGENT_TOOLS = [search_candidates, recommend_candidate]