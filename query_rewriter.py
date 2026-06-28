"""Query Rewrite（查询改写）。

结合历史对话补全指代词，使当前问题成为可独立检索的完整查询。
例如：历史讨论了「阿托品」，当前问题「它有哪些副作用」→「阿托品有哪些副作用」。
"""

import config


class QueryRewriter:
    def __init__(self, client):
        self.client = client

    def rewrite(self, question, history):
        # 没有历史，无需改写
        if not history:
            return question

        history_text = self._format(history)

        prompt = f"""你是查询改写器。任务：根据历史对话补全当前问题中的指代词，使其成为可独立检索的完整查询。

历史对话:
{history_text}

当前问题:
{question}

要求:
1. 仅补全指代（如 "它 / 这个药" → 具体药名），不要改变问题原意。
2. 不要回答问题，只输出改写后的查询，一句即可。
3. 若无需改写，原样输出当前问题。

改写结果:"""

        try:
            rsp = self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = rsp.choices[0].message.content.strip()
            return text or question
        except Exception:
            # 改写失败时安全回退到原问题，不阻断主流程
            return question

    @staticmethod
    def _format(messages):
        lines = []
        for m in messages:
            role = "用户" if m.get("role") == "user" else "助手"
            lines.append(f"{role}: {m.get('content', '')}")
        return "\n".join(lines)
