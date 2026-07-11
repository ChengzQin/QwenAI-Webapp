<!-- src/App.vue -->
<template>
  <div class="chat-container">
    <!-- 头部 -->
    <header class="chat-header">
      <div class="title">
        <span class="logo">千</span>
        <span>千问百炼 · AI 聊天</span>
        <el-tag size="small" type="success" effect="plain" style="margin-left: 4px;">
          流式输出
        </el-tag>
      </div>
      <div class="actions">
        <el-button size="small" type="primary" plain @click="exportChat">
          <el-icon><Download /></el-icon> 导出对话
        </el-button>
        <el-button size="small" plain @click="clearChat">
          <el-icon><Delete /></el-icon> 清空
        </el-button>
      </div>
    </header>

    <!-- 消息列表 -->
    <div class="chat-body" ref="chatBodyRef">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="icon">💬</div>
        <div class="hint">开始与千问百炼对话吧</div>
        <div style="font-size:13px; color:#c0c4cc;">支持文本、图片、文档附件</div>
      </div>

      <div
        v-for="(msg, idx) in messages"
        :key="idx"
        class="message-item"
        :class="msg.role"
      >
        <div class="avatar">
          {{ msg.role === 'user' ? '我' : 'AI' }}
        </div>
        <div class="bubble">
          <div class="message-content" v-html="renderMessage(msg.content)"></div>
          <!-- 附件展示 -->
          <div v-if="msg.files && msg.files.length" class="file-attachments">
            <span v-for="(f, fi) in msg.files" :key="fi" class="file-tag">
              <el-icon><Paperclip /></el-icon> {{ f.name }}
            </span>
          </div>
          <div class="timestamp">{{ formatTime(msg.timestamp) }}</div>
        </div>
      </div>

      <!-- 流式输出使用 messages 中的占位 assistant 消息展示，避免重复渲染 -->
    </div>

    <!-- 底部输入区 -->
    <footer class="chat-footer">
      <!-- 附件预览 -->
      <div v-if="uploadFiles.length" class="upload-preview">
        <div v-for="(f, idx) in uploadFiles" :key="idx" class="file-chip">
          <el-icon><Document /></el-icon>
          <span>{{ f.name }}</span>
          <span class="remove-file" @click="removeUploadFile(idx)">✕</span>
        </div>
      </div>

      <div class="input-area">
        <!-- <el-textarea
          v-model="inputText"
          placeholder="输入消息… (Shift+Enter 换行)"
          :rows="2"
          autosize
          style="min-height: 40px;"
          @keydown.enter.exact.prevent="handleSend"
          @focus="onInputFocus"
          autofocus
          :readonly="false"
          :disabled="isStreaming"
        >
        </el-textarea> -->
        <el-input
          v-model="inputText"
          type="textarea"
          placeholder="输入消息… (Shift+Enter 换行)"
          :rows="2"
          autosize
          style="min-height: 40px;"
          @keydown.enter.exact.prevent="handleSend"
          @focus="onInputFocus"
          autofocus
          :readonly="false"
          :disabled="isStreaming"
        >
        </el-input>
        <div class="action-buttons">
          <!-- 文件上传按钮 -->
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleFileChange"
            :multiple="true"
            accept=".txt,.md,.pdf,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp"
          >
            <el-button size="small" plain :disabled="isStreaming">
              <el-icon><Paperclip /></el-icon>
            </el-button>
          </el-upload>

          <el-button
            class="send-btn"
            :disabled="isStreaming || (!inputText.trim() && uploadFiles.length === 0)"
            @click="handleSend"
          >
            <el-icon><Promotion /></el-icon> 发送
          </el-button>
        </div>
      </div>
      <div style="font-size:12px; color:#c0c4cc; padding-top:6px; text-align:right;">
        支持 txt / md / pdf / doc / docx / 图片
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Promotion, Paperclip, Document, Download, Delete } from '@element-plus/icons-vue';
import { useChat } from './composables/useChat.js';
import dayjs from 'dayjs';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import katex from 'katex';
import 'katex/dist/katex.min.css';  // 样式

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
});

// 使用聊天 composable
const {
  messages,
  isStreaming,
  streamingContent,
  sendMessage,
  clearMessages,
  exportChatHistory,
  uploadFiles: uploadFilesRef,
} = useChat();

const inputText = ref('');
const chatBodyRef = ref(null);
const uploadFiles = uploadFilesRef;

// 处理文件上传
const handleFileChange = (file) => {
  // 检查文件大小 (限制 20MB)
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.warning('文件大小超过 20MB 限制');
    return;
  }
  // 检查是否已存在同名文件
  const exists = uploadFiles.value.some((f) => f.name === file.name && f.size === file.size);
  if (exists) {
    ElMessage.warning('文件已存在');
    return;
  }
  uploadFiles.value.push({
    name: file.name,
    size: file.size,
    type: file.type,
    raw: file.raw,
    url: URL.createObjectURL(file.raw),
  });
};

const removeUploadFile = (idx) => {
  uploadFiles.value.splice(idx, 1);
};

// 发送消息
const handleSend = async () => {
  const text = inputText.value.trim();
  if (!text && uploadFiles.value.length === 0) return;
  if (isStreaming.value) return;

  const files = uploadFiles.value.map((f) => ({
    name: f.name,
    size: f.size,
    type: f.type,
    data: f.raw,
  }));

  // 清空输入和附件
  inputText.value = '';
  uploadFiles.value = [];

  await sendMessage(text, files);

  // 滚动到底部
  await nextTick();
  scrollToBottom();
};

// 滚动到底部
const scrollToBottom = () => {
  if (chatBodyRef.value) {
    chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight;
  }
};

const onInputFocus = () => {
  // 仅用于调试和确保焦点能被正确处理
  // 如果需要可替换为更复杂的逻辑（如滚动或高亮）
  // 控制台日志便于在浏览器调试时查看
  // eslint-disable-next-line no-console
  console.log('input focused');
};

// 渲染消息内容 (支持 Markdown 简单转换)
// const renderMessage = (content) => {
//   if (!content) return '';
//   let html = content
//     // 代码块 ```code```
//     .replace(/```([\s\S]*?)```/g, (_, code) => {
//       return `<pre><code>${escapeHtml(code.trim())}</code></pre>`;
//     })
//     // 行内代码 `code`
//     .replace(/`([^`]+)`/g, (_, code) => {
//       return `<code>${escapeHtml(code)}</code>`;
//     })
//     // 换行转 <br>
//     .replace(/\n/g, '<br>')
//     // 链接识别 (简单)
//     .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color:#409eff;">$1</a>');

//   return html;
// };
function renderLatex(text) {
  // 先处理块级公式 $$...$$
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, latex) => {
    try {
      return katex.renderToString(latex, { displayMode: true, throwOnError: false });
    } catch (e) {
      return `<span class="katex-error">公式错误: ${latex}</span>`;
    }
  });
  // 再处理行内公式 $...$
  text = text.replace(/\$([^\$]+?)\$/g, (_, latex) => {
    try {
      return katex.renderToString(latex, { displayMode: false, throwOnError: false });
    } catch (e) {
      return `<span class="katex-error">公式错误: ${latex}</span>`;
    }
  });
  return text;
}

const renderMessage = (content) => {
  if (!content) return '';
  try {
    // 先将 LaTeX 公式转换为 KaTeX HTML，再解析 Markdown
    const contentWithLatex = renderLatex(content);
    const rawHtml = marked.parse(contentWithLatex);
    const cleanHtml = DOMPurify.sanitize(rawHtml, {
      ADD_ATTR: ['class'],
    });
    return cleanHtml;
  } catch (e) {
    console.error('Markdown解析失败:', e);
    return escapeHtml(content);
  }
};
// 简单的 HTML 转义
const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
};

// 格式化时间
const formatTime = (ts) => {
  if (!ts) return '';
  return dayjs(ts).format('HH:mm');
};

// 导出聊天
const exportChat = async () => {
  if (messages.value.length === 0) {
    ElMessage.warning('暂无聊天记录可导出');
    return;
  }
  try {
    const blob = await exportChatHistory();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${dayjs().format('YYYY-MM-DD-HHmm')}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    ElMessage.success('导出成功');
  } catch (err) {
    ElMessage.error('导出失败: ' + err.message);
  }
};

// 清空聊天
const clearChat = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有聊天记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    });
    clearMessages();
    ElMessage.success('已清空');
  } catch {
    // 取消
  }
};

// 监听消息变化滚动到底部
onMounted(() => {
  // 初始滚动
  scrollToBottom();
});

// 监听 messages 和 streamingContent 的变化，流式输出时自动滚动到底部
watch(messages, async () => {
  await nextTick();
  scrollToBottom();
}, { deep: true });

watch(streamingContent, async () => {
  await nextTick();
  scrollToBottom();
});
</script>