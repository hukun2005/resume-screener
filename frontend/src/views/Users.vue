<template>
  <AppShell
    kicker="ACCESS CONTROL"
    title="账号与权限"
    subtitle="为成员分配角色，再按角色配置可执行的操作；管理员固定拥有全部权限"
  >
    <template #actions>
      <div class="seg tab-seg">
        <button :class="{ active: tab === 'accounts' }" @click="switchTab('accounts')">
          账号管理
        </button>
        <button :class="{ active: tab === 'roles' }" @click="switchTab('roles')">角色权限</button>
        <button :class="{ active: tab === 'logs' }" @click="switchTab('logs')">操作日志</button>
      </div>
      <button v-if="tab === 'accounts'" class="btn btn-sm head-btn" @click="openCreate">
        <AppIcon name="plus" :size="15" />新建账号
      </button>
    </template>

    <div class="users-body scroll">
      <!-- ---------------------------- 账号管理 ---------------------------- -->
      <template v-if="tab === 'accounts'">
        <div v-if="loading" class="loading"><span class="loading-dot"></span>加载中…</div>

        <div v-else-if="error" class="empty-state">
          <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
          <h4>账号列表加载失败</h4>
          <p>{{ error }}</p>
          <button class="btn btn-ghost btn-sm retry-btn" @click="load">
            <AppIcon name="refresh" :size="14" />重新加载
          </button>
        </div>

        <template v-else>
          <!-- 角色概览：点击进入该角色的权限配置 -->
          <section class="role-grid">
            <button
              v-for="r in roleCards"
              :key="r.key"
              type="button"
              class="role-card"
              :data-role="r.key"
              @click="openRolePerms(r.key)"
            >
              <div class="rc-top">
                <span class="rc-ico"><AppIcon :name="r.icon" :size="17" /></span>
                <div class="rc-title">
                  <b>{{ r.label }}</b>
                  <small>{{ r.tagline }}</small>
                </div>
                <span class="rc-count">{{ roleCount(r.key) }} 人</span>
              </div>
              <ul class="rc-list">
                <li v-for="item in r.can" :key="item">
                  <AppIcon name="check" :size="13" />{{ item }}
                </li>
                <li v-if="!r.can.length" class="rc-none">暂无开通的操作</li>
                <li v-if="r.more" class="rc-none">另有 {{ r.more }} 项权限…</li>
              </ul>
              <p class="rc-note">{{ r.note }}</p>
              <span class="rc-more">
                <AppIcon name="edit" :size="13" />查看并配置权限
              </span>
            </button>
          </section>

          <!-- 账号列表 -->
          <section class="panel">
            <header class="panel-head table-head">
              <div>
                <h3 class="panel-title">
                  账号列表
                  <span v-if="roleFilter !== 'all'" class="filter-chip">
                    {{ roleLabelOf(roleFilter) }}
                    <button type="button" aria-label="清除角色筛选" @click="roleFilter = 'all'">
                      <AppIcon name="close" :size="12" />
                    </button>
                  </span>
                </h3>
                <p class="panel-sub">
                  共 {{ users.length }} 个账号 · 启用 {{ activeCount }} · 停用
                  {{ users.length - activeCount }}
                </p>
              </div>
              <div class="filters">
                <label class="search">
                  <AppIcon name="search" :size="15" />
                  <input v-model="q" placeholder="搜索账号或姓名" autocomplete="off" />
                </label>
                <div class="seg">
                  <button
                    v-for="s in STATUS_FILTERS"
                    :key="s.key"
                    :class="{ active: statusFilter === s.key }"
                    @click="statusFilter = s.key"
                  >
                    {{ s.label }}
                  </button>
                </div>
              </div>
            </header>

            <div class="table-wrap">
              <div class="table">
                <div class="tr th">
                  <span>账号</span>
                  <span>角色</span>
                  <span>状态</span>
                  <span>开通时间</span>
                  <span>操作</span>
                </div>

                <div v-for="u in filtered" :key="u.id" class="tr" :class="{ off: !u.is_active }">
                  <span class="who">
                    <span class="avatar sm">{{ (u.display_name || u.username).slice(0, 1) }}</span>
                    <span class="who-text">
                      <b>
                        {{ u.display_name }}
                        <em v-if="u.username === me">我</em>
                      </b>
                      <small class="mono">{{ u.username }}</small>
                    </span>
                  </span>

                  <span>
                    <select
                      class="role-pill"
                      :class="'r-' + u.role"
                      :value="u.role"
                      :disabled="busyId === u.id"
                      :aria-label="`${u.display_name} 的角色`"
                      @change="changeRole(u, $event.target.value)"
                    >
                      <option v-for="r in roles" :key="r.key" :value="r.key">{{ r.label }}</option>
                    </select>
                  </span>

                  <span class="state-cell">
                    <button
                      type="button"
                      class="switch"
                      :class="{ on: u.is_active }"
                      role="switch"
                      :aria-checked="u.is_active"
                      :aria-label="`${u.is_active ? '停用' : '启用'}${u.display_name}`"
                      :disabled="busyId === u.id || u.username === me"
                      @click="setActive(u, !u.is_active)"
                    >
                      <span class="knob"></span>
                    </button>
                    <small>{{ u.is_active ? '启用' : '已停用' }}</small>
                  </span>

                  <span class="date">{{ formatDate(u.created_at) }}</span>

                  <span class="ops">
                    <button class="btn btn-ghost btn-sm" @click="openReset(u)">重置密码</button>
                  </span>
                </div>

                <div v-if="!filtered.length" class="empty-state">
                  <span class="empty-ico"><AppIcon name="search" :size="22" /></span>
                  <h4>没有匹配的账号</h4>
                  <p>换个关键词，或清除角色 / 状态筛选后再试。</p>
                  <button class="btn btn-ghost btn-sm retry-btn" @click="resetFilters">清除筛选</button>
                </div>
              </div>
            </div>
          </section>
        </template>
      </template>

      <!-- ---------------------------- 角色权限 ---------------------------- -->
      <section v-else-if="tab === 'roles'" class="panel perm-panel">
        <header class="panel-head perm-head">
          <div>
            <h3 class="panel-title">角色权限配置</h3>
            <p class="panel-sub">
              勾选角色可执行的操作，保存后写入数据库；对应角色重新进入页面时生效
            </p>
          </div>
          <div class="perm-ops">
            <span v-if="dirty" class="dirty-chip"><i></i>有未保存的更改</span>
            <button
              class="btn btn-ghost btn-sm"
              :disabled="saving || !dirty"
              @click="discardChanges"
            >
              放弃更改
            </button>
            <button
              class="btn btn-ghost btn-sm"
              :disabled="saving || isAdminRole"
              @click="resetDefaults"
            >
              恢复默认
            </button>
            <button class="btn btn-sm" :disabled="saving || !dirty" @click="savePerms">
              {{ saving ? '保存中…' : '保存配置' }}
            </button>
          </div>
        </header>

        <div v-if="permLoading" class="loading"><span class="loading-dot"></span>加载权限配置…</div>

        <div v-else-if="permError" class="empty-state">
          <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
          <h4>权限配置加载失败</h4>
          <p>{{ permError }}</p>
          <button class="btn btn-ghost btn-sm retry-btn" @click="loadPermissions">
            <AppIcon name="refresh" :size="14" />重新加载
          </button>
        </div>

        <div v-else class="perm-layout">
          <aside class="perm-side">
            <button
              v-for="r in permRoles"
              :key="r.key"
              type="button"
              class="perm-role"
              :data-role="r.key"
              :class="{ active: permRole === r.key }"
              @click="permRole = r.key"
            >
              <span class="pr-ico">
                <AppIcon :name="(ROLE_META[r.key] || {}).icon || 'user'" :size="16" />
              </span>
              <span class="pr-text">
                <b>{{ r.label }}</b>
                <small>{{ r.user_count }} 个账号 · 已开通 {{ r.permissions.length }} 项</small>
              </span>
              <span v-if="r.locked" class="pr-lock" title="管理员固定拥有全部权限">
                <AppIcon name="lock" :size="12" />
              </span>
              <i v-else-if="isDirtyRole(r.key)" class="pr-dot" title="有未保存的更改"></i>
            </button>
            <p class="perm-side-note">
              角色在「账号管理」中分配给成员，这里只决定每个角色能做什么。
            </p>
          </aside>

          <div class="perm-main">
            <div class="perm-banner" :class="{ locked: isAdminRole }">
              <AppIcon :name="isAdminRole ? 'lock' : 'cap'" :size="16" />
              <p v-if="isAdminRole">
                管理员的权限固定为全部操作，不可修改；其他角色的配置保存后，管理员立即拥有最新权限。
              </p>
              <p v-else>
                「{{ currentRoleLabel }}」当前开通
                <b>{{ currentSet.size }}</b> 项权限，其中流程权限决定该角色在看板上能推进哪些环节。
              </p>
            </div>

            <div v-for="g in permGroups" :key="g.title" class="perm-group">
              <div class="pg-head">
                <h4>{{ g.title }}</h4>
                <span>{{ enabledInGroup(g) }} / {{ g.items.length }}</span>
              </div>
              <div class="pg-list">
                <button
                  v-for="item in g.items"
                  :key="item.key"
                  type="button"
                  class="perm-item"
                  role="switch"
                  :aria-checked="isOn(item.key)"
                  :aria-disabled="isLockedItem(item.key)"
                  :disabled="isLockedItem(item.key)"
                  :class="{ on: isOn(item.key), locked: isLockedItem(item.key) }"
                  @click="toggleKey(item.key)"
                >
                  <span class="pi-text">
                    <b>{{ item.label }}</b>
                    <small>{{ item.hint }}</small>
                  </span>
                  <span class="pi-state">
                    <em v-if="item.key === 'users.manage' && !isAdminRole" class="pi-badge">
                      仅管理员
                    </em>
                    <span class="switch" :class="{ on: isOn(item.key) }">
                      <span class="knob"></span>
                    </span>
                  </span>
                </button>
              </div>
            </div>

            <p class="perm-foot">
              提示：关闭「查看全部候选人」后，该角色在候选人看板与技术档案中只能看到已推送、尚未定论的候选人。
            </p>
          </div>
        </div>
      </section>

      <!-- ---------------------------- 操作日志 ---------------------------- -->
      <section v-else class="panel log-panel">
        <header class="panel-head table-head">
          <div>
            <h3 class="panel-title">操作日志</h3>
            <p class="panel-sub">记录账号与角色权限的变更来源，便于追溯谁在什么时候改了什么</p>
          </div>
          <div class="filters">
            <label class="search">
              <AppIcon name="search" :size="15" />
              <input v-model="auditQ" placeholder="搜索操作人 / 对象 / 详情" autocomplete="off" />
            </label>
            <select v-model="auditAction" class="log-select" aria-label="按操作类型筛选">
              <option value="all">全部操作</option>
              <option v-for="(label, key) in auditActions" :key="key" :value="key">
                {{ label }}
              </option>
            </select>
            <button class="btn btn-ghost btn-sm" :disabled="auditLoading" @click="loadAudit">
              <AppIcon name="refresh" :size="14" />刷新
            </button>
          </div>
        </header>

        <div v-if="auditLoading" class="loading">
          <span class="loading-dot"></span>加载操作日志…
        </div>

        <div v-else-if="auditError" class="empty-state">
          <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
          <h4>操作日志加载失败</h4>
          <p>{{ auditError }}</p>
          <button class="btn btn-ghost btn-sm retry-btn" @click="loadAudit">
            <AppIcon name="refresh" :size="14" />重新加载
          </button>
        </div>

        <template v-else>
          <div class="table-wrap">
            <div class="log-table">
              <div class="log-row lhead">
                <span>时间</span>
                <span>操作人</span>
                <span>操作</span>
                <span>对象</span>
                <span>详情</span>
              </div>

              <div v-for="log in filteredLogs" :key="log.id" class="log-row">
                <span class="date">{{ formatTime(log.created_at) }}</span>
                <span class="log-actor">
                  <b>{{ log.actor_name || log.actor }}</b>
                  <small>{{ roleLabelOf(log.actor_role) }} · {{ log.actor }}</small>
                </span>
                <span>
                  <em class="log-tag" :class="actionClass(log.action)">
                    {{ auditActions[log.action] || log.action }}
                  </em>
                </span>
                <span class="log-target" :title="log.target">{{ log.target || '—' }}</span>
                <span class="log-detail">{{ log.detail || '—' }}</span>
              </div>

              <div v-if="!filteredLogs.length" class="empty-state">
                <span class="empty-ico"><AppIcon name="clock" :size="22" /></span>
                <h4>还没有匹配的操作记录</h4>
                <p>在「账号管理」或「角色权限」中保存改动后，这里会自动留下记录。</p>
                <button class="btn btn-ghost btn-sm retry-btn" @click="resetLogFilters">
                  清除筛选
                </button>
              </div>
            </div>
          </div>
          <p class="log-foot">
            仅记录「账号与权限」页面的管理操作 · 最多展示最近 {{ auditLogs.length }} 条
          </p>
        </template>
      </section>
    </div>

    <!-- 新建账号 -->
    <div v-if="createOpen" class="mask" @click.self="closeCreate">
      <form class="dialog" @submit.prevent="createUser" @keydown.esc="closeCreate">
        <header class="dlg-head">
          <h3>新建账号</h3>
          <p>为成员开通账号并指定角色，角色决定其可操作的流程环节。</p>
          <button type="button" class="dlg-close" aria-label="关闭" @click="closeCreate">
            <AppIcon name="close" :size="16" />
          </button>
        </header>

        <div class="dlg-row">
          <label>
            <span>登录账号</span>
            <input
              ref="firstInput"
              v-model="form.username"
              class="input"
              placeholder="如 hr_wang"
              autocomplete="off"
            />
          </label>
          <label>
            <span>姓名</span>
            <input v-model="form.display_name" class="input" placeholder="如 王敏" autocomplete="off" />
          </label>
        </div>

        <div class="pick-block">
          <span class="pick-label">角色</span>
          <div class="pick-grid">
            <button
              v-for="r in roleCards"
              :key="r.key"
              type="button"
              class="pick"
              :class="{ on: form.role === r.key }"
              @click="form.role = r.key"
            >
              <span class="pick-ico"><AppIcon :name="r.icon" :size="15" /></span>
              <span class="pick-text">
                <b>{{ r.label }}</b>
                <small>{{ r.summary }}</small>
              </span>
            </button>
          </div>
        </div>

        <label class="pwd-field">
          <span>初始密码</span>
          <input
            v-model="form.password"
            type="password"
            class="input"
            placeholder="至少 6 位，创建后可请本人修改"
            autocomplete="new-password"
          />
        </label>

        <footer class="dlg-ops">
          <button type="button" class="btn btn-ghost" @click="closeCreate">取消</button>
          <button type="submit" class="btn" :disabled="creating">
            {{ creating ? '创建中…' : '创建账号' }}
          </button>
        </footer>
      </form>
    </div>

    <!-- 重置密码 -->
    <div v-if="resetFor" class="mask" @click.self="resetFor = null">
      <form class="dialog sm" @submit.prevent="submitReset" @keydown.esc="resetFor = null">
        <header class="dlg-head">
          <h3>重置「{{ resetFor.display_name }}」的密码</h3>
          <p>重置后该账号会立即下线，需要用新密码重新登录。</p>
          <button type="button" class="dlg-close" aria-label="关闭" @click="resetFor = null">
            <AppIcon name="close" :size="16" />
          </button>
        </header>
        <label class="pwd-field">
          <span>新密码</span>
          <input
            ref="resetInput"
            v-model="resetPwd"
            type="password"
            class="input"
            placeholder="至少 6 位"
            autocomplete="new-password"
          />
        </label>
        <footer class="dlg-ops">
          <button type="button" class="btn btn-ghost" @click="resetFor = null">取消</button>
          <button type="submit" class="btn" :disabled="resetPwd.length < 6">确认重置</button>
        </footer>
      </form>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { api } from '../api.js'
import { confirmAction, toast } from '../lib/ui.js'
import { user } from '../lib/auth.js'
import AppShell from '../components/AppShell.vue'
import AppIcon from '../components/AppIcon.vue'

/* 角色的产品化描述（权限判定以后端 role_permissions 为准） */
const ROLE_META = {
  admin: {
    icon: 'lock',
    tagline: '系统拥有者',
    summary: '全部流程 + 邮箱配置 + 账号管理',
    note: '系统始终保留至少一位启用状态的管理员，避免无人可管理。',
  },
  hr: {
    icon: 'user',
    tagline: '招聘流程负责人',
    summary: '默认初筛简历、推送技术部、面试通过后发 offer',
    note: '默认不参与技术部的约面与面试判定，可按需在「角色权限」中调整。',
  },
  tech: {
    icon: 'cap',
    tagline: '技术面试官',
    summary: '默认只看已推送候选人，约面与判定面试结果',
    note: '默认看不到未推送的简历，可见范围与操作项均可在「角色权限」中调整。',
  },
}

const STATUS_FILTERS = [
  { key: 'all', label: '全部' },
  { key: 'on', label: '启用' },
  { key: 'off', label: '停用' },
]

const tab = ref('accounts')

const users = ref([])
const roles = ref([])
const loading = ref(true)
const error = ref('')
const busyId = ref(null)
const q = ref('')
const roleFilter = ref('all')
const statusFilter = ref('all')
const createOpen = ref(false)
const creating = ref(false)
const resetFor = ref(null)
const resetPwd = ref('')
const firstInput = ref(null)
const resetInput = ref(null)

const form = ref({ username: '', display_name: '', role: 'hr', password: '' })

/* 权限配置 */
const permLoading = ref(true)
const permError = ref('')
const permGroups = ref([])
const permRoles = ref([])
const permRole = ref('hr')
const draft = ref({})
const saved = ref({})
const saving = ref(false)

/* 操作日志 */
const auditLogs = ref([])
const auditActions = ref({})
const auditLoading = ref(false)
const auditError = ref('')
const auditAction = ref('all')
const auditQ = ref('')
const auditLoaded = ref(false)

const me = computed(() => user.value.username)
const activeCount = computed(() => users.value.filter((u) => u.is_active).length)
const permByRole = computed(() =>
  Object.fromEntries(permRoles.value.map((r) => [r.key, r])),
)
const PERM_LABELS = computed(() => {
  const map = {}
  for (const g of permGroups.value) {
    for (const item of g.items) map[item.key] = item.label
  }
  return map
})

const roleCards = computed(() =>
  roles.value.map((r) => {
    const meta = ROLE_META[r.key] || { icon: 'user', tagline: '', note: '' }
    const keys = permByRole.value[r.key]?.permissions || []
    const labels = keys.map((k) => PERM_LABELS.value[k]).filter(Boolean)
    return {
      ...r,
      ...meta,
      can: labels.slice(0, 4),
      more: Math.max(labels.length - 4, 0),
    }
  }),
)

const currentRole = computed(() => permByRole.value[permRole.value] || null)
const currentRoleLabel = computed(() => currentRole.value?.label || permRole.value)
const isAdminRole = computed(() => permRole.value === 'admin')
const currentSet = computed(() => draft.value[permRole.value] || new Set())

const dirtyRoles = computed(() =>
  permRoles.value
    .filter((r) => !r.locked && setDiffers(draft.value[r.key], saved.value[r.key]))
    .map((r) => r.key),
)
const dirty = computed(() => dirtyRoles.value.length > 0)

const filteredLogs = computed(() => {
  const kw = auditQ.value.trim().toLowerCase()
  return auditLogs.value.filter((log) => {
    if (auditAction.value !== 'all' && log.action !== auditAction.value) return false
    if (!kw) return true
    const text = [log.actor, log.actor_name, log.target, log.detail].join(' ').toLowerCase()
    return text.includes(kw)
  })
})

const filtered = computed(() => {
  const kw = q.value.trim().toLowerCase()
  return users.value.filter((u) => {
    if (roleFilter.value !== 'all' && u.role !== roleFilter.value) return false
    if (statusFilter.value === 'on' && !u.is_active) return false
    if (statusFilter.value === 'off' && u.is_active) return false
    if (!kw) return true
    return (
      u.username.toLowerCase().includes(kw) ||
      (u.display_name || '').toLowerCase().includes(kw)
    )
  })
})

function setDiffers(a, b) {
  const x = a || new Set()
  const y = b || new Set()
  if (x.size !== y.size) return true
  for (const k of x) if (!y.has(k)) return true
  return false
}

function cloneSets(map) {
  return Object.fromEntries(Object.entries(map).map(([k, v]) => [k, new Set(v)]))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.users()
    users.value = data.users.map((u) => ({ ...u }))
    roles.value = data.roles
    if (!form.value.role) form.value.role = data.roles[0]?.key || 'hr'
  } catch (e) {
    error.value = e.message || '无法连接服务'
  } finally {
    loading.value = false
  }
}

async function loadPermissions() {
  permLoading.value = true
  permError.value = ''
  try {
    const data = await api.rolePermissions()
    permGroups.value = data.groups
    permRoles.value = data.roles.map((r) => ({ ...r, permissions: [...r.permissions] }))
    const d = {}
    const s = {}
    for (const r of permRoles.value) {
      d[r.key] = new Set(r.permissions)
      s[r.key] = new Set(r.permissions)
    }
    draft.value = d
    saved.value = s
    if (!permByRole.value[permRole.value]) {
      permRole.value = data.roles.find((r) => r.key === 'hr')?.key || data.roles[0]?.key
    }
  } catch (e) {
    permError.value = e.message || '无法连接服务'
  } finally {
    permLoading.value = false
  }
}

function switchTab(next) {
  tab.value = next
  if (next === 'logs' && !auditLoaded.value) loadAudit()
}

async function loadAudit() {
  auditLoading.value = true
  auditError.value = ''
  try {
    const data = await api.auditLogs({ limit: 100 })
    auditLogs.value = data.logs || []
    auditActions.value = data.actions || {}
    auditLoaded.value = true
  } catch (e) {
    auditError.value = e.message || '无法连接服务'
  } finally {
    auditLoading.value = false
  }
}

// 已加载过日志时，管理操作完成后顺手刷新，保证记录最新
function refreshAudit() {
  if (auditLoaded.value) loadAudit()
}

function resetLogFilters() {
  auditQ.value = ''
  auditAction.value = 'all'
}

function actionClass(action) {
  return 'a-' + String(action || '').split('.').join('-')
}

function formatTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  const p = (n) => String(n).padStart(2, '0')
  if (Number.isNaN(d.getTime())) return String(v).replace('T', ' ').slice(0, 16)
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(
    d.getHours(),
  )}:${p(d.getMinutes())}`
}

function roleCount(key) {
  return users.value.filter((u) => u.role === key).length
}

function roleLabelOf(key) {
  const hit = roles.value.find((r) => r.key === key) || permByRole.value[key]
  return hit?.label || key
}

function toggleRoleFilter(key) {
  roleFilter.value = roleFilter.value === key ? 'all' : key
}

function resetFilters() {
  q.value = ''
  roleFilter.value = 'all'
  statusFilter.value = 'all'
}

function openRolePerms(key) {
  permRole.value = key
  tab.value = 'roles'
}

function isDirtyRole(key) {
  return setDiffers(draft.value[key], saved.value[key])
}

function isLockedItem(key) {
  if (isAdminRole.value) return true
  return key === 'users.manage'
}

function isOn(key) {
  if (isAdminRole.value) return true
  if (key === 'users.manage') return false
  return currentSet.value.has(key)
}

function enabledInGroup(g) {
  return g.items.filter((item) => isOn(item.key)).length
}

function toggleKey(key) {
  if (isLockedItem(key)) return
  const role = permRole.value
  const next = new Set(draft.value[role] || [])
  if (next.has(key)) next.delete(key)
  else next.add(key)
  draft.value = { ...draft.value, [role]: next }
}

function resetDefaults() {
  if (isAdminRole.value) return
  const role = permRole.value
  draft.value = {
    ...draft.value,
    [role]: new Set(currentRole.value?.defaults || []),
  }
}

function discardChanges() {
  draft.value = cloneSets(saved.value)
}

async function savePerms() {
  if (!dirtyRoles.value.length) return
  saving.value = true
  try {
    const touched = [...dirtyRoles.value]
    for (const key of touched) {
      const list = [...(draft.value[key] || [])]
      await api.saveRolePermissions(key, list)
      saved.value = { ...saved.value, [key]: new Set(list) }
      const row = permRoles.value.find((r) => r.key === key)
      if (row) row.permissions = list.slice().sort()
    }
    const names = touched
      .map((k) => permByRole.value[k]?.label || k)
      .join('、')
    toast(`已保存 ${names} 的权限配置`, 'success')
    refreshAudit()
  } catch (e) {
    toast('保存失败：' + e.message, 'error')
    await loadPermissions()
  } finally {
    saving.value = false
  }
}

function formatDate(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v).slice(0, 10)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`
}

function openCreate() {
  form.value = { username: '', display_name: '', role: roles.value[1]?.key || 'hr', password: '' }
  createOpen.value = true
  nextTick(() => firstInput.value?.focus())
}

function closeCreate() {
  createOpen.value = false
}

async function createUser() {
  const f = form.value
  if (!f.username.trim()) return toast('请填写登录账号', 'error')
  if (f.password.length < 6) return toast('初始密码至少 6 位', 'error')
  creating.value = true
  try {
    await api.createUser({
      username: f.username.trim(),
      display_name: f.display_name.trim(),
      role: f.role,
      password: f.password,
    })
    toast(`账号 ${f.username.trim()} 已创建`, 'success')
    createOpen.value = false
    await Promise.all([load(), loadPermissions()])
    refreshAudit()
  } catch (e) {
    toast('创建失败：' + e.message, 'error')
  } finally {
    creating.value = false
  }
}

async function changeRole(u, next) {
  if (next === u.role) return
  busyId.value = u.id
  try {
    await api.updateUser(u.id, { role: next })
    u.role = next
    toast(`「${u.display_name}」的角色已改为${roleLabelOf(next)}`, 'success')
    await loadPermissions()
    refreshAudit()
  } catch (e) {
    toast('角色修改失败：' + e.message, 'error')
    await load()
  } finally {
    busyId.value = null
  }
}

async function setActive(u, next) {
  if (!next) {
    const ok = await confirmAction({
      title: `停用「${u.display_name}」？`,
      message: '停用后该账号会立即下线，且无法再登录。之后可随时重新启用。',
      confirmText: '停用账号',
      danger: true,
    })
    if (!ok) return
  }
  busyId.value = u.id
  try {
    await api.updateUser(u.id, { is_active: next })
    u.is_active = next
    toast(next ? `已启用「${u.display_name}」` : `已停用「${u.display_name}」`, 'success')
    refreshAudit()
  } catch (e) {
    toast('操作失败：' + e.message, 'error')
    await load()
  } finally {
    busyId.value = null
  }
}

function openReset(u) {
  resetFor.value = u
  resetPwd.value = ''
  nextTick(() => resetInput.value?.focus())
}

async function submitReset() {
  const u = resetFor.value
  if (!u || resetPwd.value.length < 6) return
  try {
    await api.updateUser(u.id, { password: resetPwd.value })
    toast('密码已重置，请通知本人', 'success')
    resetFor.value = null
    resetPwd.value = ''
    refreshAudit()
  } catch (e) {
    toast('重置失败：' + e.message, 'error')
  }
}

onMounted(() => {
  load()
  loadPermissions()
})
</script>

<style scoped>
.users-body {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 8px;
}

/* 让每块面板按内容高度排布，避免在受限容器里被压缩裁切 */
.users-body > .role-grid,
.users-body > .panel {
  flex: none;
}

.tab-seg button {
  height: 30px;
  padding: 0 15px;
}

.head-btn {
  height: 34px;
  padding: 0 14px;
  border-radius: 10px;
}

.loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 60px 8px;
  color: var(--text-3);
  font-size: 13px;
}

.loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--brand);
  animation: pulse-soft 1.2s ease-in-out infinite;
}

.empty-ico.err {
  background: var(--red-soft);
  color: var(--red);
}

.retry-btn {
  margin-top: 10px;
}

/* ----------------------------- 角色概览 ----------------------------- */
.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.role-card {
  --accent: var(--brand);
  --soft: var(--brand-soft);
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 18px 14px;
  text-align: left;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.14s;
}

.role-card[data-role='admin'] {
  --accent: var(--violet);
  --soft: var(--violet-soft);
}

.role-card[data-role='tech'] {
  --accent: #1f7f9c;
  --soft: #e8f4f8;
}

.role-card:hover {
  border-color: var(--accent);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.rc-top {
  display: flex;
  align-items: center;
  gap: 11px;
}

.rc-ico {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 10px;
  background: var(--soft);
  color: var(--accent);
}

.rc-title {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.rc-title b {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.rc-title small {
  font-size: 11px;
  color: var(--text-3);
}

.rc-count {
  margin-left: auto;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--soft);
  color: var(--accent);
  font-size: 11.5px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.rc-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rc-list li {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-2);
}

.rc-list .icon {
  width: 13px;
  height: 13px;
  margin-top: 3px;
  color: var(--accent);
}

.rc-list li.rc-none {
  color: var(--text-3);
  font-size: 11.5px;
  padding-left: 19px;
}

.rc-note {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px dashed var(--line-soft);
  font-size: 11.5px;
  line-height: 1.65;
  color: var(--text-3);
}

.rc-more {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--accent);
}

/* ----------------------------- 角色权限 ----------------------------- */
.perm-head {
  flex-wrap: wrap;
  row-gap: 10px;
}

.perm-ops {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.dirty-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--amber-soft, #fdf5e6);
  color: #96601a;
  font-size: 11.5px;
  font-weight: 600;
}

.dirty-chip i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c2811f;
}

.perm-layout {
  display: grid;
  grid-template-columns: 232px minmax(0, 1fr);
  gap: 16px;
  padding: 16px 18px 18px;
}

.perm-side {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.perm-role {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 11px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: #fff;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
}

.perm-role[data-role='admin'] {
  --accent: var(--violet);
  --soft: var(--violet-soft);
}

.perm-role[data-role='hr'] {
  --accent: var(--brand);
  --soft: var(--brand-soft);
}

.perm-role[data-role='tech'] {
  --accent: #1f7f9c;
  --soft: #e8f4f8;
}

.perm-role:hover {
  border-color: var(--brand-line);
}

.perm-role.active {
  border-color: var(--accent);
  background: var(--soft);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent);
}

.pr-ico {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: 9px;
  background: #f3f5fa;
  color: var(--text-2);
}

.perm-role.active .pr-ico {
  background: #fff;
  color: var(--accent);
}

.pr-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.pr-text b {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text);
}

.pr-text small {
  font-size: 10.5px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}

.pr-lock {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  flex: none;
  border-radius: 6px;
  background: var(--soft);
  color: var(--accent);
}

.pr-dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  background: #c2811f;
}

.perm-side-note {
  margin-top: 4px;
  padding: 0 2px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--text-3);
}

.perm-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.perm-banner {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 10px 12px;
  border: 1px solid var(--brand-line);
  border-radius: 10px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 12px;
  line-height: 1.65;
}

.perm-banner.locked {
  border-color: #ded6fb;
  background: var(--violet-soft);
  color: #5a40c4;
}

.perm-banner p b {
  font-variant-numeric: tabular-nums;
}

.perm-group {
  border-top: 1px solid var(--line-soft);
  padding-top: 12px;
}

.perm-group:first-of-type {
  border-top: none;
  padding-top: 0;
}

.pg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.pg-head h4 {
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--text-2);
}

.pg-head span {
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--text-3);
}

.pg-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.perm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  transition: border-color 0.18s, background 0.18s;
}

.perm-item:hover:not(:disabled) {
  border-color: var(--brand-line);
}

.perm-item.on {
  border-color: var(--brand-line);
  background: #f7f9ff;
}

.perm-item.locked {
  cursor: default;
  background: #fafbfd;
}

.pi-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pi-text b {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
}

.pi-text small {
  font-size: 11px;
  line-height: 1.55;
  color: var(--text-3);
}

.pi-state {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

.pi-badge {
  padding: 2px 7px;
  border-radius: 999px;
  background: #f3f5fa;
  color: var(--text-3);
  font-size: 10px;
  font-style: normal;
  font-weight: 600;
  white-space: nowrap;
}

.perm-item.on .pi-badge {
  background: #fff;
}

.pi-state .switch {
  width: 36px;
  height: 20px;
}

.pi-state .switch .knob {
  width: 14px;
  height: 14px;
}

.pi-state .switch.on .knob {
  transform: translateX(16px);
}

.perm-item:disabled .switch {
  opacity: 0.85;
}

.perm-foot {
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--text-3);
}

/* ----------------------------- 操作日志 ----------------------------- */
.log-select {
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  font-size: 12.5px;
  color: var(--text-2);
  cursor: pointer;
}

.log-select:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(36, 86, 230, 0.12);
}

.log-table {
  min-width: 880px;
}

.log-row {
  display: grid;
  grid-template-columns: 132px minmax(140px, 1fr) 112px minmax(150px, 1.2fr) minmax(190px, 1.8fr);
  gap: 12px;
  align-items: center;
  padding: 9px 12px;
  border-top: 1px solid var(--line-soft);
  font-size: 12px;
}

.log-row.lhead {
  border-top: none;
  padding-top: 6px;
  padding-bottom: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--text-3);
}

.log-actor {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.log-actor b {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-actor small {
  font-size: 10.5px;
  color: var(--text-3);
}

.log-tag {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: #f3f5fa;
  color: var(--text-2);
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  white-space: nowrap;
}

.log-tag.a-user-create {
  background: var(--green-soft);
  color: var(--green);
}

.log-tag.a-user-role {
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.log-tag.a-user-active {
  background: #fdf5e6;
  color: #96601a;
}

.log-tag.a-user-password {
  background: var(--red-soft);
  color: var(--red);
}

.log-tag.a-role-permissions {
  background: var(--violet-soft);
  color: #5a40c4;
}

.log-target {
  font-size: 12px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-detail {
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-2);
}

.log-foot {
  padding: 0 14px 12px;
  font-size: 11px;
  color: var(--text-3);
}

/* ----------------------------- 账号列表 ----------------------------- */
.table-head {
  flex-wrap: wrap;
  row-gap: 10px;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 22px;
  margin-left: 6px;
  padding: 0 4px 0 8px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 11px;
  font-weight: 600;
  vertical-align: middle;
}

.filter-chip button {
  display: grid;
  place-items: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  color: var(--brand-strong);
}

.filter-chip button:hover {
  background: rgba(36, 86, 230, 0.14);
}

.filters {
  display: flex;
  align-items: center;
  gap: 10px;
}

.search {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  color: var(--text-3);
  transition: border-color 0.18s, box-shadow 0.18s;
}

.search:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(36, 86, 230, 0.12);
}

.search .icon {
  width: 15px;
  height: 15px;
}

.search input {
  width: 160px;
  border: none;
  outline: none;
  background: none;
  font-size: 12.5px;
  color: var(--text);
}

.seg button {
  height: 28px;
  padding: 0 11px;
  font-size: 12px;
}

.table-wrap {
  overflow-x: auto;
  padding: 0 8px 8px;
}

.table {
  min-width: 760px;
}

.tr {
  display: grid;
  grid-template-columns: minmax(210px, 1.5fr) 132px 112px 110px 118px;
  gap: 12px;
  align-items: center;
  padding: 9px 12px;
  border-top: 1px solid var(--line-soft);
  font-size: 12.5px;
}

.tr.th {
  border-top: none;
  padding-top: 6px;
  padding-bottom: 8px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--text-3);
}

.tr.off {
  background: #fafbfd;
}

.tr.off .who,
.tr.off .date {
  opacity: 0.6;
}

.who {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.avatar.sm {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  font-size: 12.5px;
}

.who-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.who-text b {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.who-text em {
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
}

.who-text small {
  font-size: 11px;
  color: var(--text-3);
}

.mono {
  font-family: var(--mono);
}

.role-pill {
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
  cursor: pointer;
}

.role-pill.r-admin {
  border-color: #ded6fb;
  background: var(--violet-soft);
  color: #5a40c4;
}

.role-pill.r-hr {
  border-color: var(--brand-line);
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.role-pill.r-tech {
  border-color: #cfe7ef;
  background: #e8f4f8;
  color: #1d6b82;
}

.state-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.state-cell small {
  font-size: 11.5px;
  color: var(--text-3);
}

.switch {
  position: relative;
  display: inline-block;
  width: 38px;
  height: 21px;
  flex: none;
  border-radius: 999px;
  background: #dfe4ee;
  transition: background 0.18s;
}

.switch .knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 26, 48, 0.24);
  transition: transform 0.18s;
}

.switch.on {
  background: var(--green);
}

.switch.on .knob {
  transform: translateX(17px);
}

.switch:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.date {
  font-size: 11.5px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}

.ops {
  display: flex;
  gap: 6px;
}

/* ------------------------------- 弹层 ------------------------------- */
.mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(10, 18, 32, 0.42);
  backdrop-filter: blur(2px);
}

.dialog {
  width: 560px;
  max-width: 100%;
  max-height: calc(100vh - 48px);
  overflow-y: auto;
  padding: 22px 24px 20px;
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: var(--shadow-lg);
}

.dialog.sm {
  width: 400px;
}

.dlg-head {
  position: relative;
  padding-right: 32px;
}

.dlg-head h3 {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.dlg-head p {
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--text-3);
}

.dlg-close {
  position: absolute;
  top: -4px;
  right: -6px;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  color: var(--text-3);
}

.dlg-close:hover {
  background: #f2f4f9;
  color: var(--text);
}

.dlg-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 18px;
}

.dlg-row label,
.pwd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dlg-row label span,
.pwd-field span,
.pick-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-2);
}

.dlg-row .input,
.pwd-field .input {
  height: 36px;
}

.pick-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.pick-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.pick {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 11px 12px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 11px;
  background: #fff;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
}

.pick:hover {
  border-color: var(--brand-line);
}

.pick.on {
  border-color: var(--brand);
  background: var(--brand-soft);
  box-shadow: 0 0 0 3px rgba(36, 86, 230, 0.12);
}

.pick-ico {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: #f3f5fa;
  color: var(--text-2);
}

.pick.on .pick-ico {
  background: #fff;
  color: var(--brand-strong);
}

.pick-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pick-text b {
  font-size: 12.5px;
  font-weight: 700;
}

.pick-text small {
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--text-3);
}

.pwd-field {
  margin-top: 16px;
  width: 100%;
}

.dialog.sm .pwd-field {
  margin-top: 18px;
}

.dlg-ops {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

@media (max-width: 1100px) {
  .role-grid {
    grid-template-columns: 1fr;
  }

  .perm-layout {
    grid-template-columns: 1fr;
  }

  .perm-side {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .perm-role {
    flex: 1 1 180px;
  }

  .perm-side-note {
    flex: 1 1 100%;
  }

  .pg-list {
    grid-template-columns: 1fr;
  }

  .dlg-row {
    grid-template-columns: 1fr;
  }

  .pick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
