"""ChatGPT 风格的 Web UI（Gradio）。

特性：
- 左侧栏：多会话列表 / 新建对话 / 删除会话 / 知识库上传、构建与删除
- 主区：对话窗口 + 参考资料展示
- 启动时自动加载已构建的知识库

启动： python web_ui.py
"""

from pathlib import Path

import gradio as gr

import config
from models.llm import get_llm_client
from models.embeddings import get_embeddings
from conversation_manager import ConversationManager
from knowledge_base_manager import KnowledgeBaseManager
from rag_chain import RAGChain
from agent import Agent
from retriever import load_retriever
from source_formatter import SourceFormatter

# ---------- 全局组件 ----------
_client = get_llm_client()
_cm = ConversationManager(client=_client)
_embeddings = get_embeddings()
_kbm = KnowledgeBaseManager(_embeddings)


def init_agent():
    """启动时尝试加载已有知识库；没有则 RAG 链不挂检索器（仅闲聊兜底）。"""
    retriever = load_retriever(_embeddings, top_k=config.RETRIEVER_TOP_K)
    rag_chain = RAGChain(_client, retriever=retriever)
    return Agent(_client, rag_chain)


_agent = init_agent()


# ---------- 辅助 ----------
def _list_choices():
    """会话下拉框选项：(显示标题, 值=id)。"""
    convs = _cm.list_conversations()
    return [(c["title"] or "新对话", c["id"]) for c in convs]


def _kb_status():
    index_file = Path(config.VECTOR_STORE_DIR) / "index.faiss"
    if index_file.exists():
        return "✅ 知识库已加载，可正常检索问答"
    return "⚠️ 尚未构建知识库，请上传 PDF 后点击「构建知识库」"


# ---------- 事件处理 ----------
def on_new():
    """新建对话。"""
    cid = _cm.create()
    return (
        [],  # chatbot
        {"id": cid, "messages": []},  # conv_state
        gr.update(choices=_list_choices(), value=cid),  # conv_dd
        "",  # sources
    )


def on_select(cid, conv_state):
    """切换到某个历史会话。"""
    if not cid:
        return [], {"id": None, "messages": []}, ""
    data = _cm.load(cid)
    chat = [{"role": m["role"], "content": m["content"]} for m in data["messages"]]
    return chat, {"id": cid, "messages": data["messages"]}, ""


def on_delete(cid, conv_state):
    """删除下拉框中选中的会话。"""
    if cid:
        _cm.delete(cid)

    choices = _list_choices()

    if not cid or (conv_state and conv_state.get("id") == cid):
        # 删除的是当前会话（或没有选中项）：主区重置为空白对话
        return (
            gr.update(choices=choices, value=None),
            [],
            {"id": None, "messages": []},
            "",
        )

    # 删除的是其他会话：当前对话保持不变
    return (
        gr.update(choices=choices, value=conv_state.get("id")),
        gr.update(),
        conv_state,
        gr.update(),
    )


def _content_text(content):
    """从 chatbot 消息的 content 中稳健提取纯文本。

    Gradio 前端回传消息时可能把文本 content 包装成多部件列表，
    如 [{"type": "text", "text": "..."}] 或 [("text", "...")]。
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
            elif isinstance(item, (tuple, list)) and len(item) >= 2 and item[0] == "text":
                parts.append(item[1] or "")
        return "".join(parts)
    return ""


def on_send(user_msg, chat_history, conv_state):
    """发送第一步：用户消息立即上屏到对话窗口，并清空输入框。"""
    user_msg = (user_msg or "").strip()
    if not user_msg:
        return user_msg, chat_history, conv_state
    # 暂存原文：State 原样序列化，不受 chatbot 组件回传格式转换影响
    conv_state = {**(conv_state or {}), "pending": user_msg}
    chat_history = chat_history + [{"role": "user", "content": user_msg}]
    return "", chat_history, conv_state


def on_reply(chat_history, conv_state):
    """发送第二步：路由 → 生成 → 写入会话。"""
    # 最后一条不是待回复的用户消息（如空输入、重复触发）时不做任何事
    if not chat_history or chat_history[-1]["role"] != "user":
        return chat_history, conv_state, gr.update(), gr.update()

    # 优先取第一步暂存的原文；兜底从 chatbot 消息提取（content 可能被前端包装成列表）
    conv_state = dict(conv_state or {})
    user_msg = (conv_state.pop("pending", "") or _content_text(chat_history[-1]["content"])).strip()
    if not user_msg:
        return chat_history, conv_state, gr.update(), gr.update()

    # 尚未创建会话则先建一个
    if conv_state is None or not conv_state.get("id"):
        cid = _cm.create()
        conv_state = {"id": cid, "messages": []}

    history = conv_state["messages"]

    try:
        result = _agent.route(user_msg, history)
    except Exception as e:
        result = {
            "answer": f"⚠️ 处理出错：{e}",
            "sources": [],
            "rewritten": user_msg,
            "intent": "error",
        }

    answer = result["answer"]
    sources_md = SourceFormatter.to_markdown(result["sources"])

    # 写入会话
    conv_state["messages"].append({"role": "user", "content": user_msg})
    conv_state["messages"].append({"role": "assistant", "content": answer})

    title = _cm.generate_title(user_msg)
    _cm.save({"id": conv_state["id"], "title": title, "messages": conv_state["messages"]})

    chat_history = chat_history + [{"role": "assistant", "content": answer}]
    return (
        chat_history,
        conv_state,
        sources_md,
        gr.update(choices=_list_choices(), value=conv_state["id"]),
    )


def _filepath(file):
    """从 gr.File 的值里稳健地取到文件路径字符串。"""
    if isinstance(file, str):
        return file
    if isinstance(file, list) and file:
        return _filepath(file[0])
    # 兼容带 .name 属性的文件对象
    return getattr(file, "name", None)


def on_build_kb(file):
    """上传 PDF 后构建知识库，并热替换检索器。"""
    path = _filepath(file)
    if not path:
        return "⚠️ 请先上传 PDF 文件"

    try:
        retriever, n = _kbm.build(path)
        _agent.rag_chain.set_retriever(retriever)
        return f"✅ 知识库构建完成，共 {n} 个分块"
    except Exception as e:
        return f"❌ 构建失败：{e}"


def on_delete_kb(confirm):
    """删除知识库：首次点击进入确认态，再次点击才真正删除（防误删）。"""
    if not confirm:
        return (
            "⚠️ 删除后需重新上传 PDF 并构建才能恢复检索，再次点击按钮确认删除",
            True,
            gr.update(value="❗ 确认删除", variant="stop"),
        )
    try:
        _kbm.delete()
        _agent.rag_chain.set_retriever(None)  # 卸载检索器，退回无知识库状态
        status = _kb_status()
    except Exception as e:
        status = f"❌ 删除失败：{e}"
    return status, False, gr.update(value="🗑️ 删除知识库", variant="secondary")


# ---------- UI 布局 ----------
CUSTOM_CSS = """
.gradio-container {max-width: 1200px !important;}
#sidebar {background: #f7f7f8; border-radius: 12px; padding: 14px;}
"""

with gr.Blocks(title="医院药学知识助手") as demo:
    gr.Markdown("# 🏥 医院药学知识助手\n基于 RAG 的药品知识问答 · 查询改写 · 混合检索 · 记忆压缩 · 意图路由")

    conv_state = gr.State({"id": None, "messages": []})
    kb_del_confirm = gr.State(False)  # 删除知识库的二次确认标记

    with gr.Row():
        # ---- 左侧栏 ----
        with gr.Column(scale=1, min_width=240, elem_id="sidebar"):
            new_btn = gr.Button("＋ 新建对话", variant="primary")
            with gr.Row():
                conv_dd = gr.Dropdown(
                    label="历史会话",
                    choices=_list_choices(),
                    interactive=True,
                    info="点击切换历史会话；🗑️ 删除选中会话",
                    scale=5,
                    min_width=140,
                )
                del_btn = gr.Button("🗑️ 删除", size="sm", scale=1, min_width=72)

            gr.Markdown("### 📚 知识库管理")
            kb_stat = gr.Textbox(_kb_status(), label="状态", interactive=False)
            pdf_file = gr.File(label="上传 PDF 手册", file_types=[".pdf"])
            with gr.Row():
                build_btn = gr.Button("🔨 构建知识库", size="sm")
                del_kb_btn = gr.Button("🗑️ 删除知识库", size="sm")

        # ---- 主区 ----
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                [],
                label="对话",
                height=520,
            )
            sources_md = gr.Markdown("", label="参考资料")
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="输入你的问题，回车发送…",
                    scale=8,
                    show_label=False,
                    autofocus=True,
                )
                send_btn = gr.Button("发送", variant="primary", scale=1)
                clear_btn = gr.Button("清空显示", scale=1)

    # ---- 事件绑定 ----
    # 发送拆成两步：先把用户消息上屏并清空输入框，再生成回复，交互更即时
    send_inputs = [msg, chatbot, conv_state]
    send_outputs = [msg, chatbot, conv_state]
    reply_outputs = [chatbot, conv_state, sources_md, conv_dd]

    send_btn.click(on_send, send_inputs, send_outputs).then(
        on_reply, [chatbot, conv_state], reply_outputs
    )
    msg.submit(on_send, send_inputs, send_outputs).then(
        on_reply, [chatbot, conv_state], reply_outputs
    )

    new_btn.click(on_new, None, [chatbot, conv_state, conv_dd, sources_md])
    conv_dd.change(on_select, [conv_dd, conv_state], [chatbot, conv_state, sources_md])
    del_btn.click(on_delete, [conv_dd, conv_state], [conv_dd, chatbot, conv_state, sources_md])
    build_btn.click(on_build_kb, [pdf_file], [kb_stat])
    del_kb_btn.click(
        on_delete_kb, [kb_del_confirm], [kb_stat, kb_del_confirm, del_kb_btn]
    )
    clear_btn.click(lambda: ([], ""), None, [chatbot, sources_md])


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS,
    )
