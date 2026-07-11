# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .config import config
from .api import chat

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title='千问百炼 AI 聊天 API',
    description='基于 DashScope 的 AI 聊天服务，支持流式输出、文件上传',
    version='1.0.0',
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # 生产环境请限制具体域名
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# 注册路由
app.include_router(chat.router)

# 确保上传目录存在
config.ensure_upload_dir()


@app.get('/')
async def root():
    return {
        'message': '千问百炼 AI 聊天 API',
        'docs': '/docs',
        'status': 'running'
    }


@app.get('/health')
async def health():
    return {'status': 'ok'}