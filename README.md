# Qwen 百炼 AI 聊天应用

这是一个基于 FastAPI + Vue 3 + Vite + DashScope（通义千问）构建的 AI 聊天示例项目，支持流式回复、文件上传以及多模态内容处理。

## 功能特点

- 基于 DashScope 的智能聊天回复
- 流式输出，体验更接近实时对话
- 支持上传文本、PDF、Word、图片等文件
- 支持简单的对话历史管理
- 支持导出聊天记录为 Markdown
- 前后端分离，便于二次开发

## 项目结构

```text
qwen-chat-app/
├── frontend/                 # 前端 Vue 项目
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── .env                  # VITE_API_BASE
│   └── src/
│       ├── main.js
│       ├── App.vue           # 主界面
│       ├── styles/
│       │   └── global.css
│       └── composables/
│           └── useChat.js    # 聊天逻辑
└── backend/                  # 后端 Python 项目
    ├── run.py
    ├── requirements.txt
    ├── .env                  # DASHSCOPE_API_KEY 等
    └── app/
        ├── main.py
        ├── config.py
        ├── api/
        │   └── chat.py       # 流式接口
        └── utils/
            ├── qwen_client.py # 千问 SDK 封装 + 智能体逻辑
            └── tools.py       # 工具定义与执行器
```

## 环境要求

- Python 3.9+
- Node.js 18+
- npm 或 pnpm
- 阿里云 DashScope API Key

## 后端启动

1. 进入后端目录：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. 创建环境变量文件 `.env`：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
DASHSCOPE_MODEL=qwen-turbo                     # 默认模型，支持 qwen-plus, qwen-max, qwen-vl-plus等
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=20971520
```

3. 启动后端服务：

```bash
python run.py
```

后端默认会启动在：

- http://localhost:8000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 前端启动

1. 进入前端目录：

```bash
cd frontend
npm install
```

2. 可选：配置前端 API 地址，创建 `.env`：

```env
VITE_API_BASE=http://localhost:8000
```

3. 启动开发服务器：

```bash
npm run dev
```

前端默认会启动在：

- http://localhost:5173

## 主要接口

- POST /api/chat/stream：流式聊天接口
- GET /api/chat/history：获取聊天历史
- DELETE /api/chat/history：清空聊天历史

## 注意事项

- 请确保 `DASHSCOPE_API_KEY` 已正确配置，否则聊天接口将无法正常工作。
- 上传文件大小默认限制为 20MB。
- 生产环境中建议将 CORS 配置限制为具体域名。

## 开发说明

如果你想继续扩展这个项目，可以考虑加入：

- 更完整的用户认证
- 会话管理持久化
- 更丰富的文件解析能力
- 更完善的前端界面和状态管理
