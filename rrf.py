"""倒数排名融合（Reciprocal Rank Fusion）。

将多路检索结果按排名融合，得到统一排序，常用于「向量检索 + 关键词检索」混合检索。
"""


def reciprocal_rank_fusion(*ranked_lists, k=5, c=60):
    """对多路有序结果做 RRF 融合。

    Args:
        *ranked_lists: 多个 Document 列表，每个列表内越靠前相关性越高。
        k: 最终返回的结果数量。
        c: RRF 平滑常数，经验值 60。

    Returns:
        融合并去重后的前 k 个 Document（按融合分数降序），分数写入 metadata["rrf_score"]。
    """

    scores = {}
    docs = {}

    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            key = doc.page_content.strip()
            # 排名从 0 开始，公式中用 rank + 1
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank + 1)
            if key not in docs:
                docs[key] = doc

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    result = []
    for key, score in ordered[:k]:
        doc = docs[key]
        doc.metadata = dict(doc.metadata)  # 复制一份，避免污染原始对象
        doc.metadata["rrf_score"] = score
        result.append(doc)

    return result
