# 医院药学知识助手（RAG 对话助手）

基于 **检索增强生成 (RAG)** 的医院用药手册问答助手，支持查询改写、混合检索、记忆压缩、多会话管理、意图路由与知识库管理，并提供 ChatGPT 风格的 Web 界面。

## 目录结构

```
hospital_book_v1/
├── web_ui.py                # ChatGPT 风格 Web UI（Gradio）
├── agent.py                 # Agent 意图路由（QA / CHAT）
├── rag_chain.py             # RAG 主链路编排
├── retriever.py             # RAG 检索层：FAISS + BM25 混合 + RRF
├── rrf.py                   # 倒数排名融合
├── query_rewriter.py        # Query Rewrite（指代补全）
├── memory.py                # Memory 压缩（长历史摘要）
├── conversation_manager.py  # 多会话管理（JSON 持久化）
├── source_formatter.py      # 检索结果来源格式化
├── knowledge_base_manager.py# 知识库管理（PDF→切分→索引）
├── models/                  # 模型封装（LLM 客户端 / Embedding）
├── conversations/           # 会话 JSON 文件
├── kb/vector_store/         # FAISS 索引 + 持久化分块
└── config.py                # 全局配置（环境变量）
```

## 数据流

```
用户输入
  │
  ▼
Agent 路由 (agent.py)
  │  分类：QA / CHAT
  ├─ CHAT → 直接闲聊兜底
  └─ QA  → RAG 链 (rag_chain.py)
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
        ⑤ 返回答案 + 参考资料来源 (source_formatter.py)
```

会话全程由 `conversation_manager.py` 持久化到 `conversations/*.json`。

## 七大能力对照

| 需求 | 实现 |
|------|------|
| RAG 检索层 | `retriever.py`（FAISS + BM25 混合检索）+ `rrf.py`（RRF 融合） |
| Query Rewrite | `query_rewriter.py`（结合历史补全指代） |
| Memory 压缩 | `memory.py`（超阈值生成摘要 + 保留最近 N 轮） |
| 多会话管理 | `conversation_manager.py`（创建/切换/列表/标题/持久化） |
| Agent 路由 | `agent.py`（意图分类 → RAG 或闲聊） |
| ChatGPT UI | `web_ui.py`（Gradio：侧栏会话 + 上传构建 + 来源展示） |
| 知识库管理 | `knowledge_base_manager.py`（PDF 加载→切分→构建索引） |

## 安装

```bash
pip install -r requirements.txt
```

> 首次使用本地 embedding 会自动下载 `BAAI/bge-small-zh-v1.5`（约 ~100MB）。

## 配置

复制 `.env.example` 为 `.env` 并填写：

```bash
cp .env.example .env
# 编辑 .env，至少填入 LLM_API_KEY
```

默认使用 **DeepSeek** 作为 LLM，**本地 HuggingFace** 作为 embedding，开箱即用。

## 使用

### 1. 构建知识库

两种方式任选：

```bash
# 方式 A：命令行
python knowledge_base_manager.py 数据/用药手册.pdf

# 方式 B：启动 Web UI 后，在左侧栏上传 PDF → 点击「构建知识库」
```

### 2. 启动对话界面

```bash
python web_ui.py
```

浏览器自动打开 `http://localhost:7860`，即可：

- 左侧「＋ 新建对话」开新会话，下拉框切换历史会话
- 主区输入问题，回车或点「发送」
- 下方「参考资料」展示命中的来源章节/页码/相似度
- 重新上传 PDF 可随时重建知识库

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
