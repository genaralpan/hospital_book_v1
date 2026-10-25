<script setup>
import { onMounted, ref } from 'vue'
import { api } from './api'
import Sidebar from './components/Sidebar.vue'
import ChatWindow from './components/ChatWindow.vue'
import ChatInput from './components/ChatInput.vue'

// ---- 全局状态 ----
const conversations = ref([]) // [{id, title}]
const currentId = ref(null) // 当前会话 id（未发首条消息时为 null）
const messages = ref([]) // [{role, content, sources?, rewritten?}]
const sending = ref(false)
const loadError = ref('')

async function refreshConversations() {
  try {
    conversations.value = await api.listConversations()
  } catch (e) {
    loadError.value = `无法连接后端服务：${e.message}`
  }
}

// 新建对话：仅清空主区；会话在首条消息发出时由服务端惰性创建，
// 避免连点「新建」堆积空会话
function newConversation() {
  currentId.value = null
  messages.value = []
}

async function selectConversation(id) {
  if (id === currentId.value || sending.value) return
  try {
    const data = await api.getConversation(id)
    currentId.value = data.id
    messages.value = (data.messages || []).map((m) => ({
      role: m.role,
      content: m.content,
    }))
  } catch (e) {
    loadError.value = `加载会话失败：${e.message}`
  }
}

async function removeConversation(id) {
  await api.deleteConversation(id)
  if (id === currentId.value) newConversation()
  await refreshConversations()
}

async function send(text) {
  const question = (text || '').trim()
  if (!question || sending.value) return

  sending.value = true
  messages.value.push({ role: 'user', content: question })

  try {
    const rsp = await api.chat(question, currentId.value)
    currentId.value = rsp.conversation_id
    messages.value.push({
      role: 'assistant',
      content: rsp.answer,
      sources: rsp.sources || [],
      rewritten: rsp.rewritten,
    })
    await refreshConversations()
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: `⚠️ 请求失败：${e.message}`,
    })
  } finally {
    sending.value = false
  }
}

onMounted(refreshConversations)
</script>

<template>
  <div class="app">
    <Sidebar
      :conversations="conversations"
      :current-id="currentId"
      :disabled="sending"
      @new="newConversation"
      @select="selectConversation"
      @delete-conversation="removeConversation"
    />

    <main class="main">
      <header class="header">
        <h1>🏥 医院药学知识助手</h1>
        <p class="sub">基于 RAG 的药品知识问答 · 查询改写 · 混合检索 · 记忆压缩 · 意图路由</p>
      </header>

      <p v-if="loadError" class="load-error">{{ loadError }}</p>

      <ChatWindow :messages="messages" :loading="sending" @send="send" />

      <ChatInput :loading="sending" @send="send" />
    </main>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100%;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header {
  padding: 14px 24px;
  border-bottom: 1px solid var(--border);
  background: #fff;
}

.header h1 {
  font-size: 18px;
  font-weight: 600;
}

.sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-muted);
}

.load-error {
  margin: 8px 24px;
  padding: 8px 12px;
  border-radius: 8px;
  background: #fef2f2;
  color: var(--danger);
  font-size: 13px;
}
</style>
