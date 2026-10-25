<script setup>
import { nextTick, ref } from 'vue'

defineProps({
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['send'])

const text = ref('')
const el = ref(null)

// 自适应高度：随内容增高，最高 160px 后内部滚动
function resize() {
  if (!el.value) return
  el.value.style.height = 'auto'
  el.value.style.height = `${Math.min(el.value.scrollHeight, 160)}px`
}

function submit() {
  const t = text.value.trim()
  if (!t) return
  emit('send', t)
  text.value = ''
  nextTick(resize)
}

// 回车发送；Shift+回车换行
function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}
</script>

<template>
  <footer class="chat-input">
    <textarea
      ref="el"
      v-model="text"
      rows="1"
      placeholder="输入你的问题，回车发送…（Shift+回车换行）"
      :disabled="loading"
      @input="resize"
      @keydown="onKeydown"
    ></textarea>
    <button class="btn btn-primary send-btn" :disabled="loading || !text.trim()" @click="submit">
      {{ loading ? '回答中…' : '发送' }}
    </button>
  </footer>
</template>

<style scoped>
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 14px 24px 18px;
  border-top: 1px solid var(--border);
  background: #fff;
}

textarea {
  flex: 1;
  resize: none;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  max-height: 160px;
  outline: none;
  transition: border-color 0.15s;
}

textarea:focus {
  border-color: var(--primary);
}

textarea:disabled {
  background: var(--bg-page);
}

.send-btn {
  height: 42px;
  padding: 0 20px;
}
</style>
