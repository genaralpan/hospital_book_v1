"""Memory 压缩。

当历史对话过长时，把较早的部分压缩成一段摘要，只保留最近的若干轮原文，
以此控制上下文长度、节省 token。
"""

from dataclasses import dataclass

import config


@dataclass
class Memory:
    summary: str
    recent_messages: list


class MemoryManager:
    def __init__(self, client):
        self.client = client
        self.max_history = config.MEMORY_THRESHOLD
        self.keep_recent = config.MEMORY_KEEP_RECENT

    def compress(self, messages):
        """返回 Memory(summary, recent_messages)。

        - messages 长度未达阈值：summary 为空，recent_messages 为全部。
        - 达到阈值：较早部分生成摘要，recent_messages 保留最近 N 轮。
        """

        if len(messages) < self.max_history:
            return Memory(summary="", recent_messages=messages)

        old = messages[: -self.keep_recent]
        history_text = self._format(old)

        prompt = f"请用简洁中文总结以下历史对话的关键信息（涉及药品、用法用量、患者情况等），便于后续回答参考：\n\n{history_text}"

        try:
            rsp = self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            summary = rsp.choices[0].message.content.strip()
        except Exception:
            summary = ""

        return Memory(summary=summary, recent_messages=messages[-self.keep_recent:])

    @staticmethod
    def _format(messages):
        lines = []
        for m in messages:
            role = "用户" if m.get("role") == "user" else "助手"
            lines.append(f"{role}: {m.get('content', '')}")
        return "\n".join(lines)
