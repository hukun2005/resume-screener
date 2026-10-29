function token() {
  return localStorage.getItem('token')
}

function clearSession() {
  for (const k of ['token', 'username', 'display_name', 'role']) {
    localStorage.removeItem(k)
  }
}

async function request(path, options = {}) {
  const headers = {
    ...(token() ? { Authorization: 'Bearer ' + token() } : {}),
    ...(options.headers || {}),
  }
  // FormData 由浏览器自动设置 multipart 边界，不能手动指定 Content-Type
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(path, { ...options, headers })
  if (res.status === 401) {
    clearSession()
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || '请求失败')
  return data
}

export const api = {
  login: (username, password) =>
    request('/api/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: () => request('/api/me'),
  logout: () => request('/api/logout', { method: 'POST' }),
  users: () => request('/api/users'),
  createUser: (body) =>
    request('/api/users', { method: 'POST', body: JSON.stringify(body) }),
  updateUser: (id, body) =>
    request('/api/users/' + id, { method: 'PATCH', body: JSON.stringify(body) }),
  rolePermissions: () => request('/api/roles/permissions'),
  saveRolePermissions: (role, permissions) =>
    request('/api/roles/' + role + '/permissions', {
      method: 'PUT',
      body: JSON.stringify({ permissions }),
    }),
  auditLogs: (params) => {
    const qs = new URLSearchParams()
    if (params) {
      for (const k in params) {
        if (params[k]) qs.append(k, params[k])
      }
    }
    const q = qs.toString()
    return request('/api/audit/logs' + (q ? '?' + q : ''))
  },
  chat: (message) =>
    request('/api/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  chatReset: () => request('/api/chat/reset', { method: 'POST' }),
  candidates: (params) => {
    const qs = new URLSearchParams()
    if (params) {
      for (const k in params) {
        if (params[k] !== '' && params[k] != null) qs.append(k, params[k])
      }
    }
    const q = qs.toString()
    return request('/api/candidates' + (q ? '?' + q : ''))
  },
  candidate: (id) => request('/api/candidates/' + id),
  deleteCandidate: (id) =>
    request('/api/candidates/' + id, { method: 'DELETE' }),
  updateCandidateStatus: (id, status) =>
    request('/api/candidates/' + id + '/status', {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
  updateInterview: (id, body) =>
    request('/api/candidates/' + id + '/interview', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  recommendations: () => request('/api/recommendations'),
  uploadCandidate: (formData) =>
    request('/api/candidates/upload', { method: 'POST', body: formData }),
  syncEmail: () => request('/api/ingest/email/run', { method: 'POST' }),
  emailStatus: () => request('/api/ingest/email/status'),
  emailConfig: () => request('/api/ingest/email/config'),
  saveEmailConfig: (body) =>
    request('/api/ingest/email/config', { method: 'PUT', body: JSON.stringify(body) }),
  testEmailConfig: (body) =>
    request('/api/ingest/email/test', { method: 'POST', body: JSON.stringify(body) }),
}

// SSE 流式对话：读到文本片段回调 onDelta，读到工具调用回调 onTrace
export async function chatStream(message, { onDelta, onTrace, signal } = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(token() ? { Authorization: 'Bearer ' + token() } : {}),
  }
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({ message }),
    signal,
  })
  if (res.status === 401) {
    clearSession()
    window.location.href = '/login'
    throw new Error('登录已过期，请重新登录')
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.detail || '请求失败')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buf = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const chunks = buf.split('\n\n')
    buf = chunks.pop()
    for (const raw of chunks) {
      const line = raw.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (!payload) continue
      const ev = JSON.parse(payload)
      if (ev.type === 'delta') onDelta && onDelta(ev.content)
      else if (ev.type === 'trace') onTrace && onTrace(ev.trace)
      else if (ev.type === 'error') throw new Error(ev.message)
    }
  }
}