from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging

from ..config import config
from ..utils.qwen_client import QwenClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/api/chat', tags=['chat'])

# 会话历史存储（简单内存版）
session_history = {}


@router.post('/stream')
async def chat_stream(request: Request):
    """
    流式聊天接口
    - 使用 request.form() 手动解析 multipart 数据
    - 支持单个或多个文件，统一转为列表处理
    """
    # 检查 API Key
    if not config.DASHSCOPE_API_KEY or config.DASHSCOPE_API_KEY == 'sk-xxx':
        raise HTTPException(
            status_code=500,
            detail='DASHSCOPE_API_KEY 未配置，请检查后端 .env 文件。'
        )

    # 解析表单，获取文本和所有上传的文件
    form = await request.form()
    message = form.get('message') or form.get('text') or ''
    if not isinstance(message, str):
        message = str(message)

    uploaded_files = form.getlist('files')

    # 读取文件数据到内存，并校验大小
    file_infos = []
    for f in uploaded_files:
        content = await f.read()
        if len(content) > config.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f'文件 {f.filename} 超过大小限制 ({config.MAX_FILE_SIZE // 1024 // 1024}MB)'
            )
        file_infos.append({
            'name': f.filename,
            'data': content,
            'type': f.content_type or 'application/octet-stream',
        })

    # 会话 ID（可从 header 获取）
    session_id = request.headers.get('X-Session-Id', 'default')
    history = session_history.get(session_id, [])

    try:
        client = QwenClient()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 流式生成器
    async def generate():
        nonlocal history  # 🔥 关键修复：声明 history 为外部变量

        try:
            generator = client.chat_stream(
                message=message,
                files=file_infos if file_infos else None,
                history=history[-10:] if history else None,
            )

            full_content = ''
            for chunk in generator:
                if chunk:
                    full_content += chunk
                    data = json.dumps({'content': chunk}, ensure_ascii=False)
                    yield f'data: {data}\n\n'

            yield f'data: [DONE]\n\n'

            # 更新历史
            history.append({'role': 'user', 'content': message})
            history.append({'role': 'assistant', 'content': full_content})
            if len(history) > 20:
                history = history[-20:]
            session_history[session_id] = history

        except Exception as e:
            logger.error(f'流式生成出错: {e}')
            error_data = json.dumps({'error': str(e)}, ensure_ascii=False)
            yield f'data: {error_data}\n\n'

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        }
    )


@router.get('/history')
async def get_history(session_id: str = 'default'):
    return {'history': session_history.get(session_id, [])}


@router.delete('/history')
async def clear_history(session_id: str = 'default'):
    if session_id in session_history:
        session_history[session_id] = []
    return {'status': 'cleared'}