"""文本向量化与余弦相似度计算（A1 语义检索）"""
import numpy as np
from openai import OpenAI

import config

_client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)


def embed(texts):
    """把一组文本转成向量，返回 list[list[float]]（与输入顺序一致）"""
    if isinstance(texts, str):
        texts = [texts]
    resp = _client.embeddings.create(model=config.EMBEDDING_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def cosine_similarity(a, b):
    """两个向量的余弦相似度，取值约 [-1, 1]"""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))