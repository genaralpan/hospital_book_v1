"""ChatGPT 风格的 Web UI（Gradio）。

特性：
- 左侧栏：多会话列表 / 新建对话 / 知识库上传与构建
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


def on_send(user_msg, chat_history, conv_state):
    """发送消息：路由 → 生成 → 写入会话。"""
    user_msg = (user_msg or "").strip()
    if not user_msg:
        return chat_history, conv_state, "", gr.update()

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

    chat_history = chat_history + [
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": answer},
    ]
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


# ---------- UI 布局 ----------
CUSTOM_CSS = """
.gradio-container {max-width: 1200px !important;}
#sidebar {background: #f7f7f8; border-radius: 12px; padding: 14px;}
"""

with gr.Blocks(title="医院药学知识助手") as demo:
    gr.Markdown("# 🏥 医院药学知识助手\n基于 RAG 的药品知识问答 · 查询改写 · 混合检索 · 记忆压缩 · 意图路由")

    conv_state = gr.State({"id": None, "messages": []})

    with gr.Row():
        # ---- 左侧栏 ----
        with gr.Column(scale=1, min_width=240, elem_id="sidebar"):
            new_btn = gr.Button("＋ 新建对话", variant="primary")
            conv_dd = gr.Dropdown(
                label="历史会话",
                choices=_list_choices(),
                interactive=True,
                info="点击切换历史会话",
            )

            gr.Markdown("### 📚 知识库管理")
            kb_stat = gr.Textbox(_kb_status(), label="状态", interactive=False)
            pdf_file = gr.File(label="上传 PDF 手册", file_types=[".pdf"])
            build_btn = gr.Button("🔨 构建知识库")

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
    send_inputs = [msg, chatbot, conv_state]
    send_outputs = [chatbot, conv_state, sources_md, conv_dd]

    send_btn.click(on_send, send_inputs, send_outputs).then(
        lambda: gr.update(value=""), None, [msg]
    )
    msg.submit(on_send, send_inputs, send_outputs).then(
        lambda: gr.update(value=""), None, [msg]
    )

    new_btn.click(on_new, None, [chatbot, conv_state, conv_dd, sources_md])
    conv_dd.change(on_select, [conv_dd, conv_state], [chatbot, conv_state, sources_md])
    build_btn.click(on_build_kb, [pdf_file], [kb_stat])
    clear_btn.click(lambda: ([], ""), None, [chatbot, sources_md])


if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        inbrowser=True,
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS,
    )
