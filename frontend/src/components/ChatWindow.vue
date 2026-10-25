<script setup>
import { nextTick, ref, watch } from 'vue'
import MessageItem from './MessageItem.vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const el = ref(null)

// 新消息 / 加载态变化时滚动到底部
watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    el.value?.scrollTo({ top: el.value.scrollHeight, behavior: 'smooth' })
  }
)

const suggestions = [
  '阿托品的常见不良反应有哪些？',
  '地西泮过量如何解救？',
  '头孢类药品与酒精为什么会发生相互作用？',
]
</script>

<template>
  <div ref="el" class="chat-window">
    <!-- 空状态：示例问题引导 -->
    <div v-if="!messages.length && !loading" class="empty">
      <p class="empty-title">👋 你好，我是医院药学知识助手</p>
      <p class="empty-sub">先在左侧上传 PDF 手册构建知识库，然后就可以提问了</p>
      <div class="suggestions">
        <button
          v-for="s in suggestions"
          :key="s"
          class="suggestion"
          @click="emit('send', s)"
        >
          {{ s }}
        </button>
      </div>
    </div>

    <MessageItem v-for="(m, i) in messages" :key="i" :message="m" />

    <div v-if="loading" class="typing">
      <span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </div>
  </div>
</template>

<style scoped>
.chat-window {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  scroll-behavior: smooth;
}

/* ---- 空状态 ---- */
.empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
}

.empty-sub {
  font-size: 13px;
  color: var(--text-muted);
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
  max-width: 520px;
}

.suggestion {
  padding: 8px 14px;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: #fff;
  font-size: 13px;
  color: var(--text);
  transition: border-color 0.15s, color 0.15s;
}

.suggestion:hover {
  border-color: var(--primary);
  color: var(--primary);
}

/* ---- 加载中的三点动画 ---- */
.typing {
  display: flex;
  gap: 5px;
  padding: 12px 16px;
  width: fit-content;
  border-radius: var(--radius);
  background: #fff;
  border: 1px solid var(--border);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  animation: blink 1.2s infinite ease-in-out;
}

.dot:nth-child(2) {
  animation-delay: 0.2s;
}

.dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.25;
  }
  40% {
    opacity: 1;
  }
}
</style>
