"""RAG 检索层：向量(FAISS) + 关键词(BM25) 混合检索，RRF 融合。"""

import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

import config
from rrf import reciprocal_rank_fusion


class HybridRetriever:
    """向量检索 + 关键词检索的混合检索器。"""

    def __init__(self, faiss, bm25, top_k=None):
        self.faiss = faiss
        self.bm25 = bm25
        self.top_k = top_k or config.RETRIEVER_TOP_K

    def retrieve(self, query):
        faiss_docs = self.faiss.invoke(query)
        bm25_docs = self.bm25.invoke(query)
        return reciprocal_rank_fusion(faiss_docs, bm25_docs, k=self.top_k)

    def invoke(self, query):
        # 兼容 langchain retriever 接口
        return self.retrieve(query)


def _chunks_path(save_dir):
    return Path(save_dir) / "chunks.json"


def build_retriever(docs, embeddings, top_k=None, save_dir=None):
    """从分块文档构建混合检索器，并持久化（FAISS + 原始分块）。"""

    save_dir = save_dir or config.VECTOR_STORE_DIR
    top_k = top_k or config.RETRIEVER_TOP_K
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    # 1) 向量库：构建并保存
    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(save_dir)

    # 2) 持久化原始分块，供下次启动时重建 BM25（BM25 仅存在于内存）
    with open(_chunks_path(save_dir), "w", encoding="utf8") as f:
        json.dump(
            [{"content": d.page_content, "metadata": d.metadata} for d in docs],
            f,
            ensure_ascii=False,
        )

    faiss_retriever = vector_store.as_retriever(search_kwargs={"k": top_k})
    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = top_k
    return HybridRetriever(faiss_retriever, bm25, top_k=top_k)


def load_retriever(embeddings, top_k=None, save_dir=None):
    """从磁盘加载已构建的混合检索器；不存在则返回 None。"""

    save_dir = save_dir or config.VECTOR_STORE_DIR
    top_k = top_k or config.RETRIEVER_TOP_K
    index_file = Path(save_dir) / "index.faiss"

    if not index_file.exists():
        return None

    # 加载 FAISS
    vector_store = FAISS.load_local(
        save_dir, embeddings, allow_dangerous_deserialization=True
    )
    faiss_retriever = vector_store.as_retriever(search_kwargs={"k": top_k})

    # 从持久化分块重建 BM25
    with open(_chunks_path(save_dir), encoding="utf8") as f:
        raw = json.load(f)
    docs = [
        Document(page_content=c["content"], metadata=c.get("metadata", {}))
        for c in raw
    ]
    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = top_k

    return HybridRetriever(faiss_retriever, bm25, top_k=top_k)
