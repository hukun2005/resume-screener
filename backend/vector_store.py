"""基于 FAISS 的简历向量索引与语义检索（替代 O(N) 暴力余弦相似度）"""
import threading

import numpy as np
import faiss

from db import list_candidates
from embedding import embed

# 进程级缓存：FAISS 索引 + 与索引中向量一一对应的候选人 id
_cache_lock = threading.Lock()
_index = None      # faiss.IndexFlatIP 实例
_index_ids = []    # 索引中第 i 个向量对应的 candidate id


def _candidate_text(row):
    """把一个候选人拼成一段用于向量化的文本"""
    return " ".join(filter(None, [
        row.get("expected_position") or "",
        row.get("skills") or "",
        row.get("resume_text") or "",
    ]))


def _to_unit(v):
    """L2 归一化：使内积等于余弦相似度，并转为 float32"""
    v = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(v)
    return (v / n).astype(np.float32) if n > 0 else v


HNSW_THRESHOLD = 1000  # 候选人达到该数量级时改用 HNSW 近似索引，获得亚线性加速


def _build(rows):
    """根据候选人简历批量建索引，返回 (index, ids)"""
    if not rows:
        return None, []
    texts = [_candidate_text(r) for r in rows]
    vectors = [_to_unit(v) for v in embed(texts)]
    dim = vectors[0].shape[0]
    if len(vectors) >= HNSW_THRESHOLD:
        # 数据量较大时用 HNSW 近似索引，检索复杂度从 O(N) 降到约 O(log N)
        index = faiss.IndexHNSWFlat(dim, 32)  # 32：每个节点的连接数 M
        index.hnsw.efSearch = 64              # 搜索时考察的候选数量
    else:
        # 数据量小时用精确索引：内积（归一化后即余弦相似度）
        index = faiss.IndexFlatIP(dim)
    index.add(np.vstack(vectors))
    return index, [r["id"] for r in rows]


def get_index(force=False):
    """懒构建并缓存 FAISS 索引，返回 (index, ids)"""
    global _index, _index_ids
    with _cache_lock:
        if _index is None or force:
            rows = list_candidates()
            _index, _index_ids = _build(rows)
        return _index, _index_ids


def invalidate():
    """简历库变化后调用，使索引失效，下次查询重建"""
    global _index, _index_ids
    with _cache_lock:
        _index = None
        _index_ids = []


def search(query_text, top_k=5):
    """用 FAISS 检索与需求最相似的候选人，返回 [(candidate_id, score), ...]

    score 为 0~100（余弦相似度映射）。异常时返回 None，由调用方回退。
    """
    index, ids = get_index()
    if index is None or not ids:
        return None
    q = _to_unit(embed([query_text])[0]).reshape(1, -1)
    k = min(top_k, len(ids))
    scores, positions = index.search(q, k)
    results = []
    for score, pos in zip(scores[0], positions[0]):
        if pos < 0:  # 结果不足 k 时 FAISS 用 -1 占位
            continue
        results.append((ids[pos], round(max(0.0, float(score)) * 100)))
    return results