<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  message: { type: Object, required: true },
})

// 助手回复按 Markdown 渲染（先消毒防 XSS）；用户消息纯文本
const html = computed(() => {
  if (props.message.role !== 'assistant') return ''
  return DOMPurify.sanitize(marked.parse(props.message.content || ''))
})

const showSources = ref(false)
</script>

<template>
  <div class="message" :class="message.role">
    <!-- 用户消息：右侧气泡 -->
    <div v-if="message.role === 'user'" class="bubble user-bubble">
      {{ message.content }}
    </div>

    <!-- 助手消息：左侧卡片，Markdown + 参考资料 -->
    <div v-else class="assistant">
      <!-- 查询改写结果（有值且与原文不同时展示） -->
      <p v-if="message.rewritten && message.rewritten !== message.content" class="rewritten">
        🔍 检索查询：{{ message.rewritten }}
      </p>

      <div class="bubble assistant-bubble markdown-body" v-html="html"></div>

      <!-- 参考资料：可折叠卡片列表 -->
      <template v-if="message.sources && message.sources.length">
        <button class="sources-toggle" @click="showSources = !showSources">
          📚 参考资料（{{ message.sources.length }} 条）{{ showSources ? '▲' : '▼' }}
        </button>
        <div v-show="showSources" class="sources">
          <div v-for="s in message.sources" :key="s.index" class="source-card">
            <div class="source-head">
              <span class="source-index">[{{ s.index }}]</span>
              <span class="source-chapter">{{ s.chapter }}</span>
              <span v-if="s.page !== ''" class="source-page">第 {{ s.page }} 页</span>
              <span class="source-score">score={{ s.score }}</span>
            </div>
            <p class="source-content">{{ s.content }}</p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.message {
  display: flex;
  margin-bottom: 16px;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
  justify-content: flex-start;
}

.assistant {
  max-width: 86%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.bubble {
  padding: 10px 14px;
  border-radius: var(--radius);
  font-size: 14px;
  line-height: 1.7;
}

.user-bubble {
  max-width: 80%;
  background: var(--primary);
  color: #fff;
  border-bottom-right-radius: 2px;
  white-space: pre-wrap;
  word-break: break-word;
}

.assistant-bubble {
  background: #fff;
  border: 1px solid var(--border);
  border-bottom-left-radius: 2px;
  word-break: break-word;
}

/* Markdown 正文（v-html 内容需用 :deep 穿透 scoped） */
.markdown-body :deep(p) {
  margin: 0 0 8px;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(ol),
.markdown-body :deep(ul) {
  padding-left: 22px;
  margin: 4px 0;
}

.markdown-body :deep(li) {
  margin: 2px 0;
}

.markdown-body :deep(strong) {
  font-weight: 600;
}

.markdown-body :deep(code) {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--bg-sidebar);
  font-size: 13px;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 8px 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--border);
  padding: 4px 10px;
  font-size: 13px;
}

/* 查询改写提示 */
.rewritten {
  margin-bottom: 4px;
  font-size: 12px;
  color: var(--text-muted);
}

/* 参考资料 */
.sources-toggle {
  margin-top: 6px;
  font-size: 12px;
  color: var(--primary);
  padding: 2px 4px;
}

.sources-toggle:hover {
  text-decoration: underline;
}

.sources {
  width: 100%;
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.source-card {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-page);
  font-size: 13px;
}

.source-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.source-index {
  font-weight: 600;
  color: var(--primary);
}

.source-chapter {
  font-weight: 500;
}

.source-page,
.source-score {
  font-size: 12px;
  color: var(--text-muted);
}

.source-content {
  color: var(--text-muted);
  line-height: 1.5;
}
</style>
