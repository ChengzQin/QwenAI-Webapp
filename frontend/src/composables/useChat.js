// src/composables/useChat.js
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import dayjs from 'dayjs';

// 后端 API 地址 (通过环境变量配置)
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export function useChat() {
  // 消息列表
  const messages = ref([]);
  // 是否正在流式输出
  const isStreaming = ref(false);
  // 当前流式输出的内容 (用于显示)
  const streamingContent = ref('');
  // 当前流式消息的 ID (用于更新)
  let streamingMessageId = null;

  // 上传的文件列表
  const uploadFiles = ref([]);

  // 发送消息
  const sendMessage = async (text, files = []) => {
    // 添加用户消息
    const userMsg = {
      role: 'user',
      content: text || '请分析以下文件内容',
      timestamp: new Date().toISOString(),
      files: files.map((f) => ({ name: f.name, size: f.size, type: f.type })),
    };
    messages.value.push(userMsg);

    // 准备发送给后端的数据
    const formData = new FormData();
    formData.append('message', text || '');
    // 添加文件
    for (const f of files) {
      formData.append('files', f.data, f.name);
    }

    // 创建 AbortController 用于取消请求
    const controller = new AbortController();
    const signal = controller.signal;

    try {
      isStreaming.value = true;
      streamingContent.value = '';

      // 添加一个占位的 assistant 消息
      const assistantMsg = {
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        files: [],
      };
      messages.value.push(assistantMsg);
      streamingMessageId = messages.value.length - 1;

      // 使用 fetch 发送流式请求
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        body: formData,
        signal,
        // 注意: 使用 FormData 时不能设置 Content-Type，浏览器会自动设置
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`服务器错误 (${response.status}): ${errText}`);
      }

      // 读取流式响应
      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let lastStreamText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // 按行解析 (SSE 格式: data: {...}\n\n)
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') {
              // 流结束
              continue;
            }
            try {
              const data = JSON.parse(dataStr);
              if (data.content !== undefined) {
                const receivedText = String(data.content);
                const delta = receivedText.startsWith(lastStreamText)
                  ? receivedText.slice(lastStreamText.length)
                  : receivedText;

                lastStreamText = receivedText;
                if (delta) {
                  streamingContent.value += delta;
                  messages.value[streamingMessageId].content = streamingContent.value;
                }
              }
              if (data.error) {
                throw new Error(data.error);
              }
            } catch (parseErr) {
              // 如果不是 JSON，可能是纯文本数据
              if (dataStr && dataStr !== '[DONE]') {
                streamingContent.value += dataStr;
                messages.value[streamingMessageId].content = streamingContent.value;
              }
            }
          }
        }

        // 滚动到底部 (由外部组件处理)
      }

      // 流结束
      if (streamingContent.value === '') {
        // 如果没有任何内容，显示一个占位
        messages.value[streamingMessageId].content = '(无回复内容)';
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        ElMessage.warning('请求已取消');
      } else {
        ElMessage.error('发送失败: ' + err.message);
        // 移除空的 assistant 消息
        if (streamingMessageId !== null && messages.value[streamingMessageId]?.content === '') {
          messages.value.splice(streamingMessageId, 1);
        } else if (streamingMessageId !== null) {
          messages.value[streamingMessageId].content = '❌ ' + err.message;
        }
      }
    } finally {
      isStreaming.value = false;
      streamingContent.value = '';
      streamingMessageId = null;
    }
  };

  // 清空消息
  const clearMessages = () => {
    messages.value = [];
    uploadFiles.value = [];
    streamingContent.value = '';
    isStreaming.value = false;
  };

  // 导出聊天历史 (Markdown 格式)
  const exportChatHistory = () => {
    if (messages.value.length === 0) {
      throw new Error('没有聊天记录');
    }

    let markdown = '# AI 聊天记录\n\n';
    markdown += `导出时间: ${dayjs().format('YYYY-MM-DD HH:mm:ss')}\n\n`;
    markdown += '---\n\n';

    for (const msg of messages.value) {
      const roleLabel = msg.role === 'user' ? '👤 用户' : '🤖 助手';
      const time = msg.timestamp ? dayjs(msg.timestamp).format('HH:mm:ss') : '';
      markdown += `### ${roleLabel} (${time})\n\n`;
      markdown += `${msg.content}\n\n`;

      if (msg.files && msg.files.length > 0) {
        markdown += '**附件:** ' + msg.files.map((f) => `\`${f.name}\``).join(', ') + '\n\n';
      }

      markdown += '---\n\n';
    }

    return new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
  };

  return {
    messages,
    isStreaming,
    streamingContent,
    uploadFiles,
    sendMessage,
    clearMessages,
    exportChatHistory,
  };
}