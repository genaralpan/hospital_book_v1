"""多会话管理。

每个会话保存为一个 JSON 文件（conversations/<id>.json），支持创建、保存、
加载、列表、删除、自动生成标题。
"""

import json
import uuid

from pathlib import Path

import config


class ConversationManager:
    def __init__(self, client=None, root=None):
        self.client = client
        self.root = Path(root or config.CONVERSATIONS_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, cid):
        return self.root / f"{cid}.json"

    def create(self, title="新对话"):
        cid = str(uuid.uuid4())
        data = {
            "id": cid,
            "title": title,
            "messages": [],
        }
        self.save(data)
        return cid

    def save(self, data):
        with open(self._path(data["id"]), "w", encoding="utf8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load(self, cid):
        with open(self._path(cid), encoding="utf8") as f:
            return json.load(f)

    def list_conversations(self):
        """返回 [{id, title}, ...]。"""

        result = []

        for file in self.root.glob("*.json"):
            try:
                with open(file, encoding="utf8") as f:
                    data = json.load(f)
                result.append(
                    {
                        "id": data["id"],
                        "title": data.get("title", "新对话"),
                    }
                )
            except Exception:
                continue

        # 按文件名（含创建顺序）倒序，新会话在前
        result.sort(key=lambda x: x["id"], reverse=True)
        return result

    def rename(self, cid, title):
        data = self.load(cid)
        data["title"] = title
        self.save(data)

    def delete(self, cid):
        path = self._path(cid)
        if path.exists():
            path.unlink()

    def generate_title(self, first_question):
        """由 LLM 生成不超过 ~10 字的标题；失败则截断问题。"""

        if self.client:
            try:
                prompt = f"请用不超过 10 个中文字概括以下问题的主题作为会话标题，只输出标题文字：\n{first_question}"
                rsp = self.client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                title = (
                    rsp.choices[0]
                    .message.content.strip()
                    .strip("。.，,")
                    .replace("\n", "")
                )
                if title:
                    return title[:20]
            except Exception:
                pass

        return first_question[:20]
