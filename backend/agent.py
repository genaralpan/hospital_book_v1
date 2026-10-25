"""Agent 路由。

先用轻量分类判断用户意图，再决定走「知识库问答(RAG)」还是「闲聊兜底」。
没有可用知识库时，统一回退到闲聊。
"""

import config

ROUTER_PROMPT = """判断用户输入属于以下哪一类，只输出类别代号（QA 或 CHAT）：
- QA：需要查询医院 / 药学 / 药品知识库才能回答的问题（如药品用法、不良反应、适应症、相互作用）。
- CHAT：问候、闲聊、身份询问（如「你是谁」「谢谢」）等不依赖知识库的内容。

用户输入：{question}
类别："""


class Agent:
    def __init__(self, client, rag_chain):
        self.client = client
        self.rag_chain = rag_chain

    def _classify(self, question):
        """返回 'QA' 或 'CHAT'；调用失败默认 QA（宁可检索也不漏答）。"""
        try:
            rsp = self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "user", "content": ROUTER_PROMPT.format(question=question)}
                ],
                temperature=0,
            )
            label = rsp.choices[0].message.content.strip().upper()
            return "CHAT" if "CHAT" in label else "QA"
        except Exception:
            return "QA"

    def route(self, question, history=None):
        history = history or []

        # 没有知识库时，只能闲聊兜底
        if self.rag_chain is None or self.rag_chain.retriever is None:
            return self._chat(question, history, intent="no_kb")

        intent = self._classify(question)
        if intent == "CHAT":
            return self._chat(question, history, intent="chat")

        result = self.rag_chain.answer(question, history)
        result["intent"] = "qa"
        return result

    def _chat(self, question, history, intent="chat"):
        """不走知识库的直答。"""
        messages = [
            {"role": "system", "content": "你是医院药学知识助手，友好、专业地与用户交流。"}
        ]
        messages.extend(history)
        messages.append({"role": "user", "content": question})

        rsp = self.client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.5,
        )

        return {
            "answer": rsp.choices[0].message.content.strip(),
            "sources": [],
            "rewritten": question,
            "intent": intent,
        }
