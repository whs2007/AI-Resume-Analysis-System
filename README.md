# 🤖 AI 智能简历分析系统

> 星使智算科技（Sidereus AI）Python 后端/全栈实习生笔试题

基于 **FastAPI + 通义千问** 的智能简历分析系统，支持 PDF 简历自动解析、AI 关键信息提取、岗位需求智能匹配评分。

## 📋 功能概览

| 模块 | 功能 | 状态 |
|------|------|------|
| 📄 简历上传与解析 | 上传 PDF 简历，自动提取文本（支持多页） | ✅ 已完成 |
| 🔍 关键信息提取 | AI 提取姓名、电话、邮箱、求职意向、技能等 | ✅ 已完成 |
| 🎯 简历评分与匹配 | 根据岗位描述智能匹配，计算匹配度评分 | ✅ 已完成 |
| 💾 缓存机制 | Redis 缓存解析和匹配结果，避免重复计算 | ✅ 已完成 |
| 🌐 前端页面 | 简洁的 Web 交互界面，支持拖拽上传 | ✅ 已完成 |

## 🏗️ 技术架构

```
┌────────────────────────────────────────────────────┐
│                    前端 (GitHub Pages)              │
│              原生 HTML/CSS/JS 单页面应用             │
└────────────────────┬───────────────────────────────┘
                     │ RESTful API (JSON)
┌────────────────────▼───────────────────────────────┐
│              阿里云函数计算 FC (FastAPI)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ PDF 解析  │ │ AI 提取   │ │ 匹配评分  │           │
│  │ PyMuPDF  │ │ 通义千问  │ │ 通义千问  │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│               ┌──────────┐                         │
│               │Redis 缓存 │ (可选)                  │
│               └──────────┘                         │
└────────────────────────────────────────────────────┘
```

### 技术选型

| 技术 | 用途 | 选型理由 |
|------|------|----------|
| **FastAPI** | Web 框架 | 异步高性能，自动生成 API 文档，完美适配 Serverless |
| **PyMuPDF** | PDF 解析 | 中文文本提取效果好，速度快，轻量级 |
| **通义千问 (DashScope)** | AI 模型 | 中文理解能力强，与阿里云生态无缝集成，有免费额度 |
| **Redis** | 缓存 | 缓存解析和评分结果，减少重复 AI 调用成本 |
| **原生 HTML/CSS/JS** | 前端 | 零依赖，无需构建，直接部署 GitHub Pages |

## 📁 项目结构

```
resume-analyzer/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口 + 生命周期管理
│   │   ├── config.py          # 配置管理（环境变量）
│   │   ├── routers/
│   │   │   ├── resume.py      # 简历上传/查询 API
│   │   │   └── match.py       # 岗位匹配 API
│   │   ├── services/
│   │   │   ├── pdf_parser.py  # PDF 解析 + 文件验证
│   │   │   ├── ai_extractor.py # AI 关键信息提取
│   │   │   ├── matcher.py     # 岗位匹配评分
│   │   │   └── cache.py       # Redis 缓存服务
│   │   ├── models/
│   │   │   └── schemas.py     # Pydantic 数据模型
│   │   └── utils/
│   │       └── text_cleaner.py # 文本清洗工具
│   ├── requirements.txt       # Python 依赖
│   ├── Dockerfile             # 容器化部署
│   └── .env.example           # 环境变量模板
├── frontend/                   # 前端页面
│   ├── index.html             # 主页面
│   ├── css/
│   │   └── style.css          # 样式
│   └── js/
│       └── app.js             # 前端逻辑
└── README.md                   # 项目文档
```

## 🚀 本地运行

### 前置条件

- Python 3.10+
- Redis（可选，未配置时自动降级）
- 阿里云 DashScope API Key（[免费获取](https://dashscope.console.aliyun.com/apiKey)）

### 安装与启动

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DASHSCOPE_API_KEY

# 4. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 打开 API 文档
# 浏览器访问 http://localhost:8000/docs
```

### 前端使用

```bash
# 方式一：直接打开
# 浏览器打开 frontend/index.html

# 方式二：使用简单 HTTP 服务器
cd frontend
python -m http.server 3000
# 浏览器访问 http://localhost:3000
```

> **注意**：前端默认连接 `http://localhost:8000`，如需修改后端地址，编辑 `frontend/js/app.js` 中的 `API_BASE` 变量。

## ☁️ 部署指南

### 后端：阿里云函数计算 FC

#### 方式一：自定义容器（推荐）

```bash
# 1. 构建镜像
cd backend
docker build -t resume-analyzer:latest .

# 2. 推送至阿里云容器镜像服务 ACR
docker tag resume-analyzer:latest registry.cn-hangzhou.aliyuncs.com/<namespace>/resume-analyzer:latest
docker push registry.cn-hangzhou.aliyuncs.com/<namespace>/resume-analyzer:latest

# 3. 在 FC 控制台创建函数
#    - 运行环境：自定义容器
#    - 镜像地址：上述 ACR 地址
#    - 监听端口：9000
#    - 配置环境变量 DASHSCOPE_API_KEY 和 REDIS_URL
```

#### 方式二：Python 运行时 + 代码包

1. 在 FC 控制台创建函数，选择 Python 3.10 运行时
2. 上传代码包（含依赖或使用层）
3. 配置 HTTP 触发器
4. 设置环境变量

### 前端：GitHub Pages

```bash
# 1. 创建 GitHub 仓库并推送代码
# 2. 修改 frontend/js/app.js 中的 API_BASE 为 FC 触发器地址
# 3. 在仓库 Settings → Pages 中：
#    - Source: Deploy from a branch
#    - Branch: main, /frontend 文件夹
# 4. 保存后等待部署完成
```

### 环境变量

| 变量 | 说明 | 是否必需 |
|------|------|----------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API Key | ✅ 必需（否则降级为规则模式） |
| `REDIS_URL` | Redis 连接地址 | ❌ 可选（不配置则跳过缓存） |
| `HOST` | 监听地址 | ❌ 默认 0.0.0.0 |
| `PORT` | 监听端口 | ❌ 默认 8000 |

## 📡 API 文档

### 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 欢迎信息 |
| `GET` | `/api/v1/health` | 健康检查 |
| `POST` | `/api/v1/resume/upload` | 上传并解析 PDF 简历 |
| `GET` | `/api/v1/resume/{id}` | 查询已解析简历 |
| `POST` | `/api/v1/resume/{id}/match` | 简历与岗位匹配评分 |

### 调用示例

```bash
# 1. 上传简历
curl -X POST http://localhost:8000/api/v1/resume/upload \
  -F "file=@resume.pdf"

# 2. 匹配评分
curl -X POST http://localhost:8000/api/v1/resume/<resume_id>/match \
  -H "Content-Type: application/json" \
  -d '{"job_description": "Python 后端开发，3年经验，熟悉 FastAPI 和 MySQL"}'
```

启动服务后访问 `http://localhost:8000/docs` 可查看完整的 Swagger API 文档并在线调试。

## 🧠 AI 模型说明

系统使用 **阿里云通义千问 (Qwen)** 模型，通过 DashScope API 调用：

- **信息提取**：`qwen-turbo` — 速度快，成本低，适合批量简历解析
- **匹配评分**：`qwen-turbo` — 理解岗位需求，生成结构化评分和分析

### 降级策略

系统设计了完善的容错机制：
1. **AI 不可用时**：自动降级为规则匹配（正则 + 关键词）
2. **Redis 不可用时**：跳过缓存，直接计算
3. **PDF 解析异常时**：友好错误提示

## 🎨 设计亮点

1. **低耦合架构**：AI 提取、PDF 解析、匹配评分均为独立服务，便于测试和替换
2. **智能降级**：AI 或缓存不可用时不影响核心功能
3. **缓存策略**：基于文件 MD5 的缓存 key，避免相同简历重复解析
4. **文本清洗**：针对中文简历优化的清洗管道，处理断行、标点、控制字符
5. **Pydantic 验证**：全链路类型安全，自动生成 API 文档

## 📝 License

本项目仅供笔试题评估使用。
