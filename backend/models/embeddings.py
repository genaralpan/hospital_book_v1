"""Embedding 封装。

默认使用本地 HuggingFace 中文模型（BAAI/bge-small-zh-v1.5），
也可通过环境变量 EMBEDDING_PROVIDER=openai 切换到 OpenAI 在线 embedding。
"""

import config


def get_embeddings():
    provider = (config.EMBEDDING_PROVIDER or "huggingface").lower()

    if provider == "openai":
        # 延迟导入，避免未使用该后端时强依赖 langchain_openai
        from langchain_openai import OpenAIEmbeddings

        kwargs = {
            "model": config.EMBEDDING_MODEL,
            "api_key": config.OPENAI_EMBEDDING_API_KEY,
        }
        if config.OPENAI_EMBEDDING_BASE_URL:
            kwargs["base_url"] = config.OPENAI_EMBEDDING_BASE_URL
        return OpenAIEmbeddings(**kwargs)

    # 默认：本地 HuggingFace 中文 embedding
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
