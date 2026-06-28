"""RAG 主链路。

把各组件串起来：
查询改写(QueryRewriter) → 混合检索(HybridRetriever) → 记忆压缩(MemoryManager)
   → 组装 Prompt(含检索资料) → LLM 生成 → 返回答案 + 来源
"""

import config

from query_rewriter import QueryRewriter
from memory import MemoryManager
from source_formatter import SourceFormatter

SYSTEM_PROMPT = """你是医院药学知识助手，专门回答与药品、用药、药物治疗相关的问题。

回答规则：
1. 严格依据【参考资料】作答，不要编造资料中不存在的信息。
2. 若资料不足以回答，请明确说明「根据现有资料无法确定」，不要臆测。
3. 回答需专业、准确、条理清晰，必要时分点说明。
4. 涉及用法用量、禁忌、不良反应时务必谨慎，并提示遵医嘱。
5. 可在合适处标注引用来源，如 [资料1]、[资料2]。
6. 使用中文回答。"""


class RAGChain:
    def __init__(self, client, retriever=None, top_k=None):
        self.client = client
        self.retriever = retriever
        self.top_k = top_k or config.RETRIEVER_TOP_K
        self.rewriter = QueryRewriter(client)
        self.memory = MemoryManager(client)
        self.formatter = SourceFormatter()

    def set_retriever(self, retriever):
        """热更新检索器（例如在 UI 中重新构建知识库后）。"""
        self.retriever = retriever

    def answer(self, question, history=None):
        history = history or []

        # 1) 查询改写：补全指代
        rewritten = self.rewriter.rewrite(question, history)

        # 2) 混合检索
        docs = self._retrieve(rewritten)
        sources = self.formatter.format(docs)
        context = (
            "\n\n".join(f"[资料{i + 1}] {d.page_content}" for i, d in enumerate(docs))
            or "（无相关资料）"
        )

        # 3) 记忆压缩：长历史压成摘要 + 最近 N 轮原文
        mem = self.memory.compress(history)

        # 4) 组装消息
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if mem.summary:
            messages.append(
                {"role": "system", "content": f"历史对话摘要：\n{mem.summary}"}
            )
        messages.extend(mem.recent_messages)
        messages.append({"role": "system", "content": f"【参考资料】\n{context}"})
        messages.append({"role": "user", "content": rewritten})

        # 5) 生成回答
        rsp = self.client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.3,
        )

        return {
            "answer": rsp.choices[0].message.content.strip(),
            "sources": sources,
            "rewritten": rewritten,
        }

    def _retrieve(self, query):
        if self.retriever is None:
            return []
        try:
            return self.retriever.retrieve(query)
        except Exception:
            return []
