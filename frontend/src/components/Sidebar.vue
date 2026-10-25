<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../api'

defineProps({
  conversations: { type: Array, default: () => [] },
  currentId: { type: String, default: null },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['new', 'select', 'delete-conversation'])

// ---- 知识库状态（仅侧栏展示与操作，独立于会话逻辑）----
const kb = ref({ ready: false, message: '' })
const fileInput = ref(null)
const selectedFile = ref(null)
const building = ref(false)
const confirmDelete = ref(false) // 删除知识库的二次确认标记
let confirmTimer = null

onMounted(async () => {
  try {
    kb.value = await api.kbStatus()
  } catch {
    kb.value = { ready: false, message: '⚠️ 无法获取知识库状态' }
  }
})

function pickFile() {
  fileInput.value?.click()
}

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null
}

async function buildKb() {
  if (!selectedFile.value || building.value) return
  building.value = true
  try {
    kb.value = await api.kbBuild(selectedFile.value)
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
  } catch (e) {
    kb.value = { ...kb.value, message: `❌ ${e.message}` }
  } finally {
    building.value = false
  }
}

async function deleteKb() {
  if (building.value) return
  if (!confirmDelete.value) {
    // 首次点击进入确认态，5 秒未确认自动复位（防误删）
    confirmDelete.value = true
    clearTimeout(confirmTimer)
    confirmTimer = setTimeout(() => (confirmDelete.value = false), 5000)
    return
  }
  clearTimeout(confirmTimer)
  confirmDelete.value = false
  try {
    kb.value = await api.kbDelete()
  } catch (e) {
    kb.value = { ...kb.value, message: `❌ ${e.message}` }
  }
}
</script>

<template>
  <aside class="sidebar">
    <button class="btn btn-primary new-btn" :disabled="disabled" @click="emit('new')">
      ＋ 新建对话
    </button>

    <!-- 历史会话 -->
    <p class="section-title">历史会话</p>
    <ul class="conv-list">
      <li
        v-for="c in conversations"
        :key="c.id"
        class="conv-item"
        :class="{ active: c.id === currentId }"
        @click="emit('select', c.id)"
      >
        <span class="conv-title" :title="c.title">{{ c.title || '新对话' }}</span>
        <button
          class="conv-del"
          title="删除会话"
          :disabled="disabled"
          @click.stop="emit('delete-conversation', c.id)"
        >
          🗑
        </button>
      </li>
      <li v-if="!conversations.length" class="conv-empty">暂无历史会话</li>
    </ul>

    <!-- 知识库管理 -->
    <div class="kb-panel">
      <p class="section-title">📚 知识库管理</p>
      <p class="kb-status" :class="kb.ready ? 'ok' : 'warn'">{{ kb.message }}</p>
      <input
        ref="fileInput"
        type="file"
        accept=".pdf"
        class="hidden-input"
        @change="onFileChange"
      />
      <button class="btn btn-ghost kb-pick" :title="selectedFile?.name" @click="pickFile">
        {{ selectedFile ? selectedFile.name : '选择 PDF 手册' }}
      </button>
      <div class="kb-actions">
        <button class="btn btn-ghost" :disabled="!selectedFile || building" @click="buildKb">
          {{ building ? '构建中…' : '🔨 构建知识库' }}
        </button>
        <button
          class="btn"
          :class="confirmDelete ? 'btn-danger' : 'btn-ghost'"
          :disabled="building"
          @click="deleteKb"
        >
          {{ confirmDelete ? '❗ 确认删除' : '🗑 删除知识库' }}
        </button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  padding: 14px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  overflow-y: auto;
}

.new-btn {
  width: 100%;
}

.section-title {
  margin: 16px 2px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

/* ---- 会话列表 ---- */
.conv-list {
  list-style: none;
  flex: 1;
  min-height: 60px;
  overflow-y: auto;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  margin-bottom: 2px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.conv-item:hover {
  background: #e8eaee;
}

.conv-item.active {
  background: #dbeafe;
  color: var(--primary-dark);
  font-weight: 500;
}

.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-del {
  visibility: hidden;
  font-size: 13px;
  color: var(--text-muted);
  padding: 2px 4px;
  border-radius: 4px;
}

.conv-item:hover .conv-del {
  visibility: visible;
}

.conv-del:hover {
  color: var(--danger);
}

.conv-empty {
  padding: 8px 10px;
  font-size: 13px;
  color: var(--text-muted);
}

/* ---- 知识库面板 ---- */
.kb-panel {
  border-top: 1px solid var(--border);
  padding-top: 4px;
}

.kb-status {
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 10px;
}

.kb-status.ok {
  color: #059669;
}

.kb-status.warn {
  color: #d97706;
}

.hidden-input {
  display: none;
}

.kb-pick {
  width: 100%;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-muted);
}

.kb-actions {
  display: flex;
  gap: 8px;
}

.kb-actions .btn {
  flex: 1;
  padding: 8px 6px;
  font-size: 13px;
}
</style>
