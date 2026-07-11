# backend/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """应用配置"""
    # DashScope API Key
    DASHSCOPE_API_KEY = os.getenv('DASHSCOPE_API_KEY', '')
    # 模型名称
    MODEL = os.getenv('DASHSCOPE_MODEL', 'qwen-turbo')
    # 上传目录
    UPLOAD_DIR = os.getenv('UPLOAD_DIR', './uploads')
    # 最大文件大小 (20MB)
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 20 * 1024 * 1024))
    # API 前缀
    API_PREFIX = '/api'

    @classmethod
    def ensure_upload_dir(cls):
        """确保上传目录存在"""
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)

config = Config()