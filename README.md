# 医院药学知识助手（RAG 对话助手）

基于 **检索增强生成 (RAG)** 的医院用药手册问答助手，支持查询改写、混合检索、记忆压缩、多会话管理、意图路由与知识库管理。

**前后端分离架构**：后端为 FastAPI REST API，前端为 Vue 3 + Vite 的 ChatGPT 风格界面。

## 目录结构

```
hospital_book_v1/
├── backend/                      # 后端（Python / FastAPI）
│   ├── main.py                   # REST API 入口（uvicorn 启动）
│   ├── agent.py                  # Agent 意图路由（QA / CHAT）
│   ├── rag_chain.py              # RAG 主链路编排
│   ├── retriever.py              # RAG 检索层：FAISS + BM25 混合 + RRF
│   ├── rrf.py                    # 倒数排名融合
│   ├── query_rewriter.py         # Query Rewrite（指代补全 + 口语规范化）
│   ├── memory.py                 # Memory 压缩（长历史摘要）
│   ├── conversation_manager.py   # 多会话管理（JSON 持久化）
│   ├── source_formatter.py       # 检索结果来源格式化
│   ├── knowledge_base_manager.py # 知识库管理（PDF→切分→索引）
│   ├── models/                   # 模型封装（LLM 客户端 / Embedding）
│   ├── conversations/            # 会话 JSON 文件（运行时数据）
│   ├── kb/vector_store/          # FAISS 索引 + 持久化分块（运行时数据）
│   └── requirements.txt
├── frontend/                     # 前端（Vue 3 + Vite）
│   ├── src/
│   │   ├── App.vue               # 布局与全局状态
│   │   ├── api.js                # REST API 封装
│   │   └── components/           # Sidebar / ChatWindow / MessageItem / ChatInput
│   └── vite.config.js            # 开发代理 /api → 127.0.0.1:8000
├── .env                          # 配置（密钥等，勿提交）
└── .env.example
```

## 数据流

```
用户输入（Vue 前端 → POST /api/chat）
  │
  ▼
Agent 路由 (backend/agent.py)
  │  分类：QA / CHAT
  ├─ CHAT → 直接闲聊兜底
  └─ QA  → RAG 链 (backend/rag_chain.py)
            │
            ▼
        ① 查询改写 (query_rewriter.py)   ← 历史：补全「它/这个药」等指代
            │
            ▼
        ② 混合检索 (retriever.py)        ← FAISS(语义) + BM25(关键词)，RRF 融合
            │
            ▼
        ③ 记忆压缩 (memory.py)            ← 长历史压成摘要 + 最近 N 轮原文
            │
            ▼
        ④ 组装 Prompt + 检索资料 → LLM 生成
            │
            ▼
        ⑤ 返回答案 + 参考资料来源 (source_formatter.py) → 前端 Markdown 渲染
```

会话全程由 `conversation_manager.py` 持久化到 `backend/conversations/*.json`。

## REST API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/conversations` | 会话列表 |
| POST | `/api/conversations` | 新建会话 |
| GET | `/api/conversations/{id}` | 会话详情（含消息） |
| DELETE | `/api/conversations/{id}` | 删除会话 |
| POST | `/api/chat` | 发送消息（未传会话 id 时惰性创建） |
| GET | `/api/kb/status` | 知识库状态 |
| POST | `/api/kb/build` | 上传 PDF 并构建知识库（multipart） |
| DELETE | `/api/kb` | 删除知识库 |

## 七大能力对照

| 需求 | 实现 |
|------|------|
| RAG 检索层 | `retriever.py`（FAISS + BM25 混合检索）+ `rrf.py`（RRF 融合） |
| Query Rewrite | `query_rewriter.py`（结合历史补全指代） |
| Memory 压缩 | `memory.py`（超阈值生成摘要 + 保留最近 N 轮） |
| 多会话管理 | `conversation_manager.py` + `Sidebar.vue`（创建/切换/列表/删除） |
| Agent 路由 | `agent.py`（意图分类 → RAG 或闲聊） |
| ChatGPT UI | Vue 3 前端（侧栏会话 + 上传构建 + Markdown + 来源卡片） |
| 知识库管理 | `knowledge_base_manager.py` + `/api/kb/*`（PDF→切分→构建索引） |

## 安装

后端（Python 3.10+）：

```bash
pip install -r backend/requirements.txt
```

前端（Node 18+）：

```bash
cd frontend
npm install
```

> 首次使用本地 embedding 会自动下载 `BAAI/bge-small-zh-v1.5`（约 ~100MB）。
> 若 huggingface.co 不可达且模型已缓存，可设置 `HF_HUB_OFFLINE=1` 离线启动；
> 首次下载可走镜像 `HF_ENDPOINT=https://hf-mirror.com`。

## 配置

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
# 编辑 .env，至少填入 LLM_API_KEY
```

默认使用 **DeepSeek** 作为 LLM，**本地 HuggingFace** 作为 embedding，开箱即用。

## 使用

### 1. 启动后端（端口 8000）

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 2. 启动前端（开发模式，端口 5173）

```bash
cd frontend
npm run dev
```

浏览器打开 `http://localhost:5173`，即可：

- 左侧「＋ 新建对话」开新会话，点击切换历史会话，悬停 🗑 删除
- 主区输入问题，回车发送（Shift+回车换行）
- 助手回复下方可展开「参考资料」卡片（章节 / 页码 / 融合得分）
- 左侧「知识库管理」：选择 PDF → 构建知识库（构建中可随时删除重建）

### 3. 生产部署（可选，单服务）

```bash
cd frontend && npm run build   # 构建产物输出到 frontend/dist
cd ../backend && python -m uvicorn main:app --port 8000
```

构建产物存在时，FastAPI 会自动托管 `frontend/dist`，直接访问 `http://localhost:8000` 即可，无需单独部署前端。

### 4. 命令行构建知识库（可选）

```bash
cd backend
python knowledge_base_manager.py 数据/用药手册.pdf
```

## 配置项一览（环境变量）

| 变量 | 默认 | 说明 |
|------|------|------|
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | LLM 服务地址（兼容 OpenAI 协议） |
| `LLM_API_KEY` | — | LLM 密钥 |
| `LLM_MODEL` | `deepseek-chat` | 模型名 |
| `EMBEDDING_PROVIDER` | `huggingface` | `huggingface` / `openai` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | embedding 模型 |
| `RETRIEVER_TOP_K` | `5` | 每路召回及最终返回数 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `500` / `50` | 文本切分参数 |
| `MEMORY_THRESHOLD` / `MEMORY_KEEP_RECENT` | `20` / `10` | 触发压缩轮数 / 保留轮数 |
