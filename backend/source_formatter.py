"""检索结果（来源）格式化。把 Document 列表整理成结构化卡片 / Markdown。"""

from pathlib import Path


class SourceFormatter:
    @staticmethod
    def format(docs):
        """转成前端友好的卡片结构。"""

        cards = []

        for i, doc in enumerate(docs):
            meta = doc.metadata or {}
            chapter = meta.get("chapter") or meta.get("source", "未知来源")
            # source 可能是构建时的绝对路径（如上传临时目录），展示时只取文件名
            if "\\" in chapter or "/" in chapter:
                chapter = Path(chapter).stem
            cards.append(
                {
                    "index": i + 1,
                    "chapter": chapter,
                    "page": meta.get("page", ""),
                    "score": round(float(meta.get("rrf_score", 0.0)), 4),
                    "content": doc.page_content[:150].replace("\n", " "),
                }
            )

        return cards

    @staticmethod
    def to_markdown(cards):
        """卡片转 Markdown，用于 UI 展示。"""

        if not cards:
            return ""

        lines = ["**📚 参考资料**"]
        for c in cards:
            page = f" · 第{c['page']}页" if c["page"] != "" else ""
            lines.append(
                f"- **[{c['index']}]** {c['chapter']}{page} `score={c['score']}`\n"
                f"  > {c['content']}"
            )
        return "\n".join(lines)
