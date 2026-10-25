/** 后端 REST API 封装（开发期经 Vite 代理，生产可同域部署）。 */

const BASE = '/api'

async function request(path, options = {}) {
  const rsp = await fetch(`${BASE}${path}`, options)
  if (!rsp.ok) {
    let detail = `HTTP ${rsp.status}`
    try {
      const body = await rsp.json()
      detail = body.detail || detail
    } catch {
      /* 非 JSON 响应体，忽略 */
    }
    throw new Error(detail)
  }
  return rsp.json()
}

function jsonOptions(body) {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export const api = {
  // ---- 会话 ----
  listConversations: () => request('/conversations'),
  getConversation: (id) => request(`/conversations/${id}`),
  deleteConversation: (id) =>
    request(`/conversations/${id}`, { method: 'DELETE' }),

  // ---- 对话 ----
  chat: (message, conversationId = null) =>
    request('/chat', jsonOptions({ message, conversation_id: conversationId })),

  // ---- 知识库 ----
  kbStatus: () => request('/kb/status'),
  kbBuild: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/kb/build', { method: 'POST', body: form })
  },
  kbDelete: () => request('/kb', { method: 'DELETE' }),
}
