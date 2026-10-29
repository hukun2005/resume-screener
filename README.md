# AI 简历筛选助手（resume-screener）

面向面试官 / HR 的 AI 简历筛选系统。招聘者用自然语言描述用人需求，系统自动从简历库中做**语义检索**并推荐最匹配的候选人，支持流式对话、简历详情查看与 PDF / Word 简历上传解析。

## ✨ 功能特性

- **登录鉴权**：Token 认证 + SHA-256 密码哈希，多个账号隔离会话
- **AI 对话式筛选**：基于 Function Calling 的 Agent，让大模型自主决定调用「简历检索 / 推荐候选人」工具
- **向量语义检索**：BGE-M3 Embedding + FAISS，按语义召回候选人（而非关键词硬匹配）
- **流式输出**：SSE 逐字渲染 AI 答复，前端实时展示
- **多轮对话历史管理**：滑动窗口 + LLM 摘要压缩，控制 token 开销、避免上下文超限
- **简历上传解析**：PDF / Word 自动提取文本入库，新增简历实时参与检索

## 🛠 技术栈

| 层 | 技术 |
|:---|:---|
| 前端 | Vue 3 · Vite · Vue Router |
| 后端 | FastAPI · Uvicorn |
| AI | LangChain · LangGraph · OpenAI 兼容接口（Qwen2.5-7B-Instruct）· BGE-M3 Embedding |
| 检索 | FAISS · NumPy（余弦相似度） |
| 存储 | MySQL（pymysql） |
| 解析 | pypdf · python-docx |

## 📁 目录结构

```
resume-screener/
├── backend/
│   ├── app.py            # FastAPI 入口与 REST/SSE 接口
│   ├── agent.py          # LangGraph ReAct Agent + 多轮历史管理
│   ├── tools.py          # 简历检索 / 推荐工具（@tool 声明）
│   ├── vector_store.py   # FAISS 向量索引与检索
│   ├── embedding.py      # BGE-M3 向量化
│   ├── resume_parser.py  # PDF / Word 文本提取
│   ├── db.py             # MySQL 连接、建表、种子数据
│   ├── auth.py           # 密码哈希与 Token 认证
│   └── config.py         # 环境变量读取
└── frontend/
    └── src/
        ├── views/        # Login / Workbench / CandidateDetail
        ├── components/   # AgentChat / CandidateCard
        ├── api.js        # 接口封装（自动携带 Token）
        └── router.js     # 路由与登录守卫
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0

### 1. 后端

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt

# 复制环境变量模板并填写真实值（API Key、MySQL 密码）
cp .env.example .env

# 初始化数据库（建库建表 + 写入种子简历）
python init_db.py

# 启动服务（默认 127.0.0.1:8000）
python app.py
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev   # 默认 http://localhost:5173
```

> 前端已将 `/api` 代理到 `http://127.0.0.1:8000`，两个进程需同时运行。

## 🔑 环境变量

在 `backend/.env` 中配置：

| 变量 | 说明 |
|:---|:---|
| `OPENAI_API_KEY` | OpenAI 兼容接口的 API Key |
| `OPENAI_BASE_URL` | 接口地址，默认 `https://api.siliconflow.cn/v1` |
| `MODEL` | 对话模型，默认 `Qwen/Qwen2.5-7B-Instruct` |
| `EMBEDDING_MODEL` | 向量模型，默认 `BAAI/bge-m3` |
| `MYSQL_HOST` / `MYSQL_PORT` | MySQL 连接信息 |
| `MYSQL_USER` / `MYSQL_PASSWORD` | MySQL 账号密码 |
| `MYSQL_DB` | 数据库名，默认 `resume_screener` |
| `IMAP_HOST` / `IMAP_PORT` | 收简历的 IMAP 服务器（如 `imap.qq.com:993`），留空则关闭邮箱收件 |
| `IMAP_USER` / `IMAP_PASSWORD` | 邮箱账号与 IMAP 授权码（不是登录密码） |
| `IMAP_SEARCH_DAYS` | 每次同步回溯的邮件天数，默认 7 |
| `IMAP_POLL_INTERVAL` | 定时同步间隔（秒），默认 300，设为 0 只允许手动触发 |

## 📮 邮箱收件（接入主流招聘平台）

招聘平台的「简历转发到邮箱」都会把简历作为 PDF/Word 附件发到 HR 邮箱，因此无需平台 API 授权：

1. 在 `.env` 填好 `IMAP_*` 配置，启动后端即自动开始定时同步；
2. 也可随时手动触发：`POST /api/ingest/email/run`；
3. 查看同步状态与处理明细：`GET /api/ingest/email/status`、`GET /api/ingest/email/log`。

入库时按手机号 / 邮箱查重，同一封邮件的同一附件只处理一次（`email_ingest_log` 表保证幂等）。

## 👤 默认演示账号

| 账号 | 密码 |
|:---|:---|
| `admin` | `123456` |
| `hukun` | `12345678` |

## 💡 技术亮点

1. **Agent 工具调用**：用 LangGraph 的 `create_react_agent` 编排，简历检索 / 推荐以 `@tool` 声明，模型自主决策调用时机与参数。
2. **向量检索**：简历向量 L2 归一化后存入 FAISS，内积即余弦相似度；数据量小时用精确索引 `IndexFlatIP`，量大时自动切换 HNSW 近似索引，检索复杂度从 O(N) 降到约 O(log N)。
3. **多轮历史管理**：滑动窗口保留最近 8 轮完整对话，更早历史用 LLM 压缩为滚动摘要注入系统提示词，既控 token 又不丢关键上下文。
4. **流式 + 工具调用清洗**：SSE 流式输出过程中过滤工具调用遗留的 `</tool_call>` 等杂质片段，保证前端渲染干净。

## ⚠️ 安全说明

`backend/.env` 包含真实 API Key 与数据库密码，已被 `.gitignore` 排除，**请勿提交到仓库**。