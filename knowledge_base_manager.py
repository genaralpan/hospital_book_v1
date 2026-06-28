"""知识库管理。

PDF → 加载 → 清洗切分 → 向量化构建索引（混合检索）。
"""

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config
from retriever import build_retriever


class KnowledgeBaseManager:
    def __init__(self, embeddings):
        self.embeddings = embeddings

    def load(self, pdf_path):
        """加载 PDF（按页切分，metadata 含 page）。"""

        loader = PyPDFLoader(pdf_path)
        return loader.load()

    def split(self, docs, chunk_size=None, chunk_overlap=None):
        """递归切分，并补充 chapter 等元数据。"""

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size or config.CHUNK_SIZE,
            chunk_overlap=chunk_overlap or config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "；", "，", " ", ""],
        )
        chunks = splitter.split_documents(docs)

        for ch in chunks:
            meta = ch.metadata
            meta.setdefault("source", "医院用药手册")
            if "chapter" not in meta:
                meta["chapter"] = meta.get("source", "医院用药手册")

        return chunks

    def build(self, pdf_path, chunk_size=None, chunk_overlap=None):
        """完整构建流程：加载 → 切分 → 构建并持久化检索器。返回 (retriever, 分块数)。"""

        docs = self.load(pdf_path)
        chunks = self.split(docs, chunk_size, chunk_overlap)
        retriever = build_retriever(chunks, self.embeddings, top_k=config.RETRIEVER_TOP_K)
        return retriever, len(chunks)


if __name__ == "__main__":
    # 命令行直接构建：python knowledge_base_manager.py 数据/手册.pdf
    import sys

    from models.embeddings import get_embeddings

    pdf = sys.argv[1] if len(sys.argv) > 1 else r"D:\resources\40临床药理学 第8版.pdf"
    mgr = KnowledgeBaseManager(get_embeddings())
    _, count = mgr.build(pdf)
    print(f"✅ 知识库构建完成，共 {count} 个分块")
