"""LLM 客户端（OpenAI 兼容协议，默认指向 DeepSeek）。"""

from openai import OpenAI

import config


def get_llm_client() -> OpenAI:
    """返回一个配置好 base_url / api_key 的 OpenAI 客户端。"""

    return OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
    )
