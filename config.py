"""
全局配置。

优先读取环境变量（.env 文件），其次使用默认值。
默认 LLM 走 DeepSeek（兼容 OpenAI 协议），embedding 走本地 HuggingFace 中文模型。
"""

import os
from pathlib import Path

# 可选：自动加载 .env
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# ---------- LLM（默认 DeepSeek，兼容 OpenAI 协议）----------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# ---------- Embedding ----------
# huggingface（本地、免费、适合中文） | openai（API 在线）
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
OPENAI_EMBEDDING_BASE_URL = os.getenv("OPENAI_EMBEDDING_BASE_URL", "")
OPENAI_EMBEDDING_API_KEY = os.getenv(
    "OPENAI_EMBEDDING_API_KEY", os.getenv("OPENAI_API_KEY", "")
)

# ---------- 检索 ----------
RETRIEVER_TOP_K = int(os.getenv("RETRIEVER_TOP_K", "5"))  # 每路召回 + 最终返回数量
RRF_CONSTANT = int(os.getenv("RRF_CONSTANT", "60"))  # RRF 平滑常数

# ---------- 文本切分 ----------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ---------- 记忆压缩 ----------
MEMORY_THRESHOLD = int(os.getenv("MEMORY_THRESHOLD", "20"))  # 超过该轮数触发压缩
MEMORY_KEEP_RECENT = int(os.getenv("MEMORY_KEEP_RECENT", "10"))  # 压缩后保留的最近轮数

# ---------- 路径 ----------
BASE_DIR = Path(__file__).resolve().parent
VECTOR_STORE_DIR = str(BASE_DIR / "kb" / "vector_store")
CONVERSATIONS_DIR = str(BASE_DIR / "conversations")
