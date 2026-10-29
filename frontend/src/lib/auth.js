// 当前登录账号与角色（localStorage 持久化，刷新后用 /api/me 校正）
import { computed, ref } from 'vue'
import { api } from '../api.js'
import { ROLE_LABELS, setRolePermissions } from './flow.js'

const state = ref({
  username: localStorage.getItem('username') || '',
  display_name: localStorage.getItem('display_name') || '',
  role: localStorage.getItem('role') || '',
})

export const user = state
export const role = computed(() => state.value.role)
export const roleLabel = computed(() => ROLE_LABELS[state.value.role] || '未分配角色')
export const isAdmin = computed(() => state.value.role === 'admin')
export const isTech = computed(() => state.value.role === 'tech')
export const isHR = computed(() => state.value.role === 'hr')
export const canScreen = computed(() => ['admin', 'hr'].includes(state.value.role))

export function setUser(data) {
  if (data.token) localStorage.setItem('token', data.token)
  const next = {
    username: data.username || state.value.username,
    display_name: data.display_name || data.username || state.value.display_name,
    role: data.role || state.value.role,
  }
  state.value = next
  localStorage.setItem('username', next.username)
  localStorage.setItem('display_name', next.display_name)
  localStorage.setItem('role', next.role)
  if (Array.isArray(data.permissions)) {
    setRolePermissions({ [next.role]: new Set(data.permissions) })
  }
}

export function clearUser() {
  state.value = { username: '', display_name: '', role: '' }
  setRolePermissions(null)
  for (const k of ['token', 'username', 'display_name', 'role']) {
    localStorage.removeItem(k)
  }
}

// 刷新页面后向服务端确认角色（管理员改了角色能立即生效）
export async function syncUser() {
  if (!localStorage.getItem('token')) return
  try {
    const me = await api.me()
    setUser(me)
  } catch {
    // 401 已由 api 层跳转登录，其余错误先沿用本地缓存
  }
}

// 登录后的默认落地页：技术部直接进看板
export function homePath() {
  return state.value.role === 'tech' ? '/kanban' : '/'
}
