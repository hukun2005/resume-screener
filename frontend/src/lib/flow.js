import { ref } from 'vue'

// 阶段定义与流转权限（与后端 permissions.py 保持一致）
export const STEPS = [
  { key: 'new', label: '新简历', owner: 'hr', color: '#7c8798', tint: '#f1f4f9' },
  { key: 'screening', label: 'HR 初筛', owner: 'hr', color: '#2456e6', tint: '#eaf0ff' },
  { key: 'tech_review', label: '待技术评估', owner: 'tech', color: '#2f8aa8', tint: '#e8f4f8' },
  { key: 'interview', label: '面试中', owner: 'tech', color: '#6c52d4', tint: '#efecfd' },
  { key: 'tech_passed', label: '面试通过待定 offer', owner: 'hr', color: '#c2811f', tint: '#fdf5e6' },
  { key: 'offered', label: '已通过', owner: 'hr', color: '#0f8a68', tint: '#e6f6f0' },
  { key: 'rejected', label: '已淘汰', owner: 'hr', color: '#cc3d3d', tint: '#fdeaea' },
]

export const STEPS_BY_KEY = Object.fromEntries(STEPS.map((s) => [s.key, s]))

export const FINAL_STATUSES = ['offered', 'rejected']

// 技术部可见的阶段：HR 已推送、尚未有终局结论
export const TECH_VISIBLE = ['tech_review', 'interview', 'tech_passed']

export const ROLE_LABELS = { admin: '管理员', hr: 'HR', tech: '技术面试官' }
export const OWNER_LABELS = { hr: 'HR 负责', tech: '技术部负责', admin: '管理员' }

// 面试形式（与后端 INTERVIEW_MODES 对应）
export const INTERVIEW_MODES = [
  { key: 'onsite', label: '现场' },
  { key: 'video', label: '视频' },
  { key: 'phone', label: '电话' },
]

export const INTERVIEW_MODE_LABELS = Object.fromEntries(
  INTERVIEW_MODES.map((m) => [m.key, m.label]),
)

// from -> { to: 允许的角色 }（默认矩阵，仅用于文案提示）
export const TRANSITIONS = {
  new: { screening: ['hr', 'admin'], rejected: ['hr', 'admin'] },
  screening: { tech_review: ['hr', 'admin'], rejected: ['hr', 'admin'] },
  tech_review: {
    screening: ['hr', 'admin'],
    interview: ['tech', 'admin'],
    rejected: ['tech', 'admin'],
  },
  interview: { tech_passed: ['tech', 'admin'], rejected: ['tech', 'admin'] },
  tech_passed: { offered: ['hr', 'admin'], rejected: ['hr', 'admin'] },
  offered: {},
  rejected: {},
}

// 阶段流转对应的权限 key（与后端 TRANSITION_PERMISSIONS 一致）
const TRANSITION_PERM = {
  'new>screening': 'stage.screen',
  'screening>tech_review': 'stage.push_tech',
  'tech_review>screening': 'stage.push_tech',
  'tech_review>interview': 'stage.schedule',
  'interview>tech_passed': 'stage.interview_result',
  'tech_passed>offered': 'stage.offer',
}

// 管理员在「角色权限」页配置的结果：{ hr: Set, tech: Set }；为 null 表示尚未加载
export const rolePermissions = ref(null)

export function setRolePermissions(map) {
  rolePermissions.value = map || null
}

export function hasPerm(role, key) {
  if (role === 'admin') return true
  const set = rolePermissions.value?.[role]
  if (!set) return false
  return set.has(key)
}

export function canViewAll(role) {
  if (role === 'admin') return true
  const set = rolePermissions.value?.[role]
  if (!set) return role !== 'tech'
  return set.has('candidate.view_all')
}

export function canMove(role, from, to) {
  if (!to || from === to) return false
  if (role === 'admin') return true
  if (!rolePermissions.value) {
    return (TRANSITIONS[from] || {})[to]?.includes(role) || false
  }
  if (to === 'rejected') {
    return !FINAL_STATUSES.includes(from) && hasPerm(role, 'stage.reject')
  }
  const key = TRANSITION_PERM[`${from}>${to}`]
  return key ? hasPerm(role, key) : false
}

export function targetsOf(role, from) {
  return STEPS.map((s) => s.key).filter((to) => canMove(role, from, to))
}

// 该角色能推进到哪些阶段（用于按钮提示）
export function rolesFor(from, to) {
  return (TRANSITIONS[from] || {})[to] || []
}

export function labelOf(key) {
  return STEPS_BY_KEY[key]?.label || key
}

// 当前角色在某个候选人上「下一步该做什么」
export function nextActionHint(role, status) {
  if (status === 'offered' || status === 'rejected') return '流程已结束'
  const targets = targetsOf(role, status)
  if (!targets.length) {
    const owner = STEPS_BY_KEY[status]?.owner
    return owner === 'tech' ? '等待技术部处理' : '等待 HR 处理'
  }
  return ''
}
