# backend/app/utils/qwen_client.py
import dashscope
from dashscope import Generation, MultiModalConversation
import json
import logging
from typing import Generator, Optional, List, Dict, Any

from ..config import config

logger = logging.getLogger(__name__)

# 设置 API Key
dashscope.api_key = config.DASHSCOPE_API_KEY


class QwenClient:
    """千问百炼 API 客户端"""

    def __init__(self, model: str = None):
        self.model = model or config.MODEL
        self._validate_api_key()

    def _validate_api_key(self):
        """验证 API Key 是否配置"""
        if not config.DASHSCOPE_API_KEY or config.DASHSCOPE_API_KEY == 'sk-xxx':
            raise ValueError(
                'DASHSCOPE_API_KEY 未配置或无效，请检查 .env 文件。'
                '请访问 https://dashscope.aliyun.com/ 获取 API Key。'
            )

    def chat_stream(
        self,
        message: str,
        files: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Generator[str, None, None]:
        """
        流式聊天
        :param message: 用户消息
        :param files: 文件列表 [{'name': 'a.jpg', 'data': bytes, 'type': 'image/jpeg'}, ...]
        :param history: 历史消息 [{'role': 'user', 'content': '...'}, ...]
        :yield: 流式内容片段
        """
        # 检测是否有多模态内容 (图片)
        has_image = False
        image_data_list = []
        text_files_content = []

        if files:
            for f in files:
                file_type = f.get('type', '')
                if file_type.startswith('image/'):
                    has_image = True
                    # 读取图片数据 (base64)
                    import base64
                    b64 = base64.b64encode(f['data']).decode('utf-8')
                    image_data_list.append({
                        'image': f'data:{file_type};base64,{b64}',
                        'text': f'[图片: {f["name"]}]'
                    })
                else:
                    # 文本类文件, 提取内容
                    text_content = self._extract_text_from_file(f)
                    if text_content:
                        text_files_content.append(f'【文件 {f["name"]} 内容】\n{text_content}')

        # 构建消息
        if has_image:
            # 多模态模式 (使用 qwen-vl-plus 或 qwen-vl-max)
            # 注意: 多模态模型需要单独指定
            model_for_multimodal = 'qwen-vl-plus'
            # 构建多模态消息
            user_content = []
            # 添加图片
            for img in image_data_list:
                user_content.append({'image': img['image']})
                if img['text']:
                    user_content.append({'text': img['text']})
            # 添加文本
            full_text = message
            if text_files_content:
                full_text += '\n\n' + '\n\n'.join(text_files_content)
            user_content.append({'text': full_text})

            messages = [{'role': 'user', 'content': user_content}]

            # 调用多模态 API
            return self._call_multimodal_stream(messages, model_for_multimodal)
        else:
            # 纯文本模式
            # 构建消息
            full_text = message
            if text_files_content:
                full_text += '\n\n' + '\n\n'.join(text_files_content)

            # 构建历史消息 (如果有)
            messages = []
            if history:
                messages.extend(history)
            messages.append({'role': 'user', 'content': full_text})

            return self._call_text_stream(messages)

    def _call_text_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """调用文本模型流式 API"""
        try:
            self._last_stream_text = ''
            response = Generation.call(
                model=self.model,
                messages=messages,
                stream=True,
                result_format='message',
            )

            for chunk in response:
                if chunk.output and chunk.output.choices:
                    choice = chunk.output.choices[0]
                    if choice.message and choice.message.content:
                        content = choice.message.content
                        if isinstance(content, str):
                            if self._last_stream_text and content.startswith(self._last_stream_text):
                                delta = content[len(self._last_stream_text):]
                            else:
                                delta = content
                            self._last_stream_text = content
                            if delta:
                                yield delta

        except Exception as e:
            logger.error(f'调用千问 API 失败: {e}')
            yield f'[错误] {str(e)}'

    def _call_multimodal_stream(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """调用多模态模型流式 API"""
        try:
            self._last_stream_text = ''
            response = MultiModalConversation.call(
                model=model,
                messages=messages,
                stream=True,
            )

            for chunk in response:
                if chunk.output and chunk.output.choices:
                    choice = chunk.output.choices[0]
                    if choice.message and choice.message.content:
                        # 多模态返回的内容可能是列表
                        content = choice.message.content
                        if isinstance(content, list):
                            for item in content:
                                if 'text' in item:
                                    text_piece = item['text']
                                    if self._last_stream_text and text_piece.startswith(self._last_stream_text):
                                        delta = text_piece[len(self._last_stream_text):]
                                    else:
                                        delta = text_piece
                                    self._last_stream_text = text_piece
                                    if delta:
                                        yield delta
                        elif isinstance(content, str):
                            if self._last_stream_text and content.startswith(self._last_stream_text):
                                delta = content[len(self._last_stream_text):]
                            else:
                                delta = content
                            self._last_stream_text = content
                            if delta:
                                yield delta

        except Exception as e:
            logger.error(f'调用多模态 API 失败: {e}')
            yield f'[错误] {str(e)}'

    def _extract_text_from_file(self, file_info: Dict) -> Optional[str]:
        """从文件中提取文本内容"""
        name = file_info.get('name', '')
        data = file_info.get('data', b'')
        file_type = file_info.get('type', '')

        if not data:
            return None

        try:
            # 根据文件类型提取文本
            if name.lower().endswith('.txt') or name.lower().endswith('.md'):
                return data.decode('utf-8', errors='ignore')

            elif name.lower().endswith('.pdf'):
                import io
                from PyPDF2 import PdfReader
                reader = PdfReader(io.BytesIO(data))
                text = ''
                for page in reader.pages:
                    text += page.extract_text() or ''
                return text[:5000]  # 限制长度

            elif name.lower().endswith('.docx'):
                import io
                from docx import Document
                doc = Document(io.BytesIO(data))
                text = '\n'.join([p.text for p in doc.paragraphs])
                return text[:5000]

            elif name.lower().endswith('.doc'):
                # .doc 格式较复杂, 简单提示
                return '[无法提取 .doc 文件内容，请转换为 .docx 或 .txt 格式]'

            else:
                # 其他文件类型返回文件名提示
                return f'[文件: {name}]'

        except Exception as e:
            logger.warning(f'提取文件 {name} 文本失败: {e}')
            return f'[无法提取文件内容: {name}]'