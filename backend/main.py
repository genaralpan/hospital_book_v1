"""FastAPI 后端入口（前后端分离）。

- 后端（本文件）：提供 REST API，复用原有 RAG 核心模块
- 前端：frontend/ 下的 Vue 3 应用，开发时由 Vite 将 /api 代理到本服务

接口一览：
- GET    /api/health                 健康检查
- GET    /api/conversations          会话列表
- POST   /api/conversations          新建会话
- GET    /api/conversations/{cid}    加载会话详情
- DELETE /api/conversations/{cid}    删除会话
- POST   /api/chat                   发送消息（路由 → 生成 → 落盘）
- GET    /api/kb/status              知识库状态
- POST   /api/kb/build               上传 PDF 并构建知识库
- DELETE /api/kb                     删除知识库

启动：
    cd backend
    python -m uvicorn main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from agent import Agent
from conversation_manager import ConversationManager
from knowledge_base_manager import KnowledgeBaseManager
from models.embeddings import get_embeddings
from models.llm import get_llm_client
from rag_chain import RAGChain
from retriever import load_retriever

app = FastAPI(title="医院药学知识助手 API")

# 开发期前端跑在 Vite (5173)；生产部署可按需收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 全局组件（启动时加载已有知识库）----------
_client = get_llm_client()
_cm = ConversationManager(client=_client)
_embeddings = get_embeddings()
_kbm = KnowledgeBaseManager(_embeddings)


def _init_agent():
    """启动时尝试加载已有知识库；没有则 RAG 链不挂检索器（仅闲聊兜底）。"""
    retriever = load_retriever(_embeddings, top_k=config.RETRIEVER_TOP_K)
    rag_chain = RAGChain(_client, retriever=retriever)
    return Agent(_client, rag_chain)


_agent = _init_agent()


# ---------- 请求 / 响应模型 ----------
class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


# ---------- 健康检查 ----------
@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------- 会话管理 ----------
@app.get("/api/conversations")
def list_conversations():
    return _cm.list_conversations()


@app.post("/api/conversations")
def create_conversation():
    cid = _cm.create()
    return {"id": cid, "title": "新对话", "messages": []}


@app.get("/api/conversations/{cid}")
def get_conversation(cid: str):
    try:
        return _cm.load(cid)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="会话不存在")


@app.delete("/api/conversations/{cid}")
def delete_conversation(cid: str):
    _cm.delete(cid)
    return {"ok": True}


# ---------- 对话 ----------
@app.post("/api/chat")
def chat(req: ChatRequest):
    """发送消息：加载会话 → 路由生成 → 写回会话。

    未传 conversation_id 时在服务端惰性创建会话，
    避免用户连点「新建对话」产生一堆空会话。
    """
    question = (req.message or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="消息不能为空")

    if req.conversation_id:
        try:
            data = _cm.load(req.conversation_id)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="会话不存在")
    else:
        data = {"id": _cm.create(), "title": "新对话", "messages": []}

    history = data["messages"]
    is_first_turn = not history  # 先记录：append 之后 history 就非空了

    try:
        result = _agent.route(question, history)
    except Exception as e:
        result = {
            "answer": f"⚠️ 处理出错：{e}",
            "sources": [],
            "rewritten": question,
            "intent": "error",
        }

    data["messages"].append({"role": "user", "content": question})
    data["messages"].append({"role": "assistant", "content": result["answer"]})

    # 首轮消息自动生成标题（后续轮次沿用，避免标题随每轮漂移）
    if is_first_turn:
        data["title"] = _cm.generate_title(question)

    _cm.save(data)

    return {
        "conversation_id": data["id"],
        "title": data["title"],
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "rewritten": result.get("rewritten"),
        "intent": result.get("intent"),
    }


# ---------- 知识库管理 ----------
def _kb_ready():
    return (Path(config.VECTOR_STORE_DIR) / "index.faiss").exists()


def _kb_status_body():
    if _kb_ready():
        return {"ready": True, "message": "✅ 知识库已加载，可正常检索问答"}
    return {"ready": False, "message": "⚠️ 尚未构建知识库，请上传 PDF 后点击「构建知识库」"}


@app.get("/api/kb/status")
def kb_status():
    return _kb_status_body()


@app.post("/api/kb/build")
def kb_build(file: UploadFile):
    """上传 PDF 并构建知识库，完成后热替换检索器。

    同步 def：FastAPI 会放进线程池执行，不阻塞事件循环
    （PDF 解析 + 向量化耗时较长）。
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="请上传 PDF 文件")

    # 先落盘再构建；只取文件名，防止路径穿越
    upload_dir = Path(config.BASE_DIR) / "kb" / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / Path(file.filename).name
    with open(dest, "wb") as f:
        f.write(file.file.read())

    try:
        retriever, n = _kbm.build(str(dest))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"构建失败：{e}")

    _agent.rag_chain.set_retriever(retriever)
    return {"ready": True, "chunks": n, "message": f"✅ 知识库构建完成，共 {n} 个分块"}


@app.delete("/api/kb")
def kb_delete():
    """删除知识库并卸载检索器，退回无知识库状态。"""
    try:
        _kbm.delete()
        _agent.rag_chain.set_retriever(None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败：{e}")
    return _kb_status_body()


# ---------- 可选：托管前端构建产物（生产可单服务部署）----------
# 若 frontend/dist 存在（npm run build 产物），则由本服务直接托管，
# 无需单独部署前端；API 路由先注册，不受影响。
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
