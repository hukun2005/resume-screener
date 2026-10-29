<template>
  <AppShell
    kicker="CANDIDATE PROFILE"
    :title="c ? c.name : '简历详情'"
    :subtitle="c ? c.expected_position || '未填写意向岗位' : '正在读取候选人档案'"
  >
    <template #actions>
      <button class="btn btn-ghost btn-sm" @click="$router.push(backPath)">
        <AppIcon name="arrowLeft" :size="14" />{{ backLabel }}
      </button>
      <button v-if="c && hasPerm(role, 'candidate.delete')" class="btn btn-danger" @click="remove">
        <AppIcon name="trash" :size="15" />删除
      </button>
    </template>

    <div class="detail-body scroll">
      <div v-if="!c && !loadError" class="loading">
        <span class="loading-dot"></span>加载中…
      </div>

      <div v-else-if="loadError" class="empty-state">
        <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
        <h4>档案加载失败</h4>
        <p>{{ loadError }}</p>
        <button class="btn btn-ghost btn-sm retry-btn" @click="load">
          <AppIcon name="refresh" :size="14" />重新加载
        </button>
      </div>

      <template v-else>
        <div class="detail-grid">
          <div class="col-main">
            <section class="panel profile">
              <div class="profile-top">
                <span class="avatar profile-avatar" :style="avatarStyle">{{ initial }}</span>
                <div class="profile-id">
                  <h2>{{ c.name }}</h2>
                  <p><AppIcon name="briefcase" :size="13" />{{ c.expected_position || '未填写意向岗位' }}</p>
                </div>
                <span class="status" :class="'s-' + status">{{ statusLabel }}</span>
              </div>

              <dl class="facts">
                <div class="fact">
                  <dt><AppIcon name="cap" :size="15" />最高学历</dt>
                  <dd>{{ c.education || '—' }}</dd>
                </div>
                <div class="fact">
                  <dt><AppIcon name="briefcase" :size="15" />工作经历</dt>
                  <dd>{{ c.experience || '—' }}</dd>
                </div>
                <div class="fact">
                  <dt><AppIcon name="phone" :size="15" />联系电话</dt>
                  <dd>
                    <a v-if="c.phone" :href="'tel:' + c.phone">{{ c.phone }}</a>
                    <span v-else>—</span>
                  </dd>
                </div>
                <div class="fact">
                  <dt><AppIcon name="at" :size="15" />邮箱</dt>
                  <dd>
                    <a v-if="c.email" :href="'mailto:' + c.email">{{ c.email }}</a>
                    <span v-else>—</span>
                  </dd>
                </div>
              </dl>

              <div v-if="skillList.length" class="skill-block">
                <h4>核心技能</h4>
                <div class="tags">
                  <span v-for="s in skillList" :key="s" class="tag">{{ s }}</span>
                </div>
              </div>
            </section>

            <section v-if="showInterview" class="panel interview">
              <header class="panel-head">
                <div>
                  <h3 class="panel-title">面试安排</h3>
                  <p class="panel-sub">时间、形式与面试反馈由技术部维护，HR 只读</p>
                </div>
                <span class="iv-flag" :class="ivAt ? 'set' : 'unset'">
                  <AppIcon :name="ivAt ? 'clock' : 'alert'" :size="12" />
                  {{ ivAt ? fmtInterview(ivAt) : '尚未安排' }}
                </span>
              </header>

              <form v-if="canEditInterview" class="iv-form" @submit.prevent="saveInterview">
                <div class="iv-row">
                  <label class="iv-field">
                    <span>面试时间</span>
                    <input v-model="iv.at" type="datetime-local" class="input" />
                  </label>
                  <div class="iv-field">
                    <span>面试形式</span>
                    <div class="seg iv-seg">
                      <button
                        v-for="m in INTERVIEW_MODES"
                        :key="m.key"
                        type="button"
                        :class="{ active: iv.mode === m.key }"
                        @click="iv.mode = m.key"
                      >
                        {{ m.label }}
                      </button>
                    </div>
                  </div>
                  <label class="iv-field">
                    <span>面试官</span>
                    <input v-model="iv.interviewer" class="input" placeholder="如 李工" />
                  </label>
                </div>

                <label class="iv-field">
                  <span>面试反馈</span>
                  <textarea
                    v-model="iv.feedback"
                    class="input iv-area"
                    rows="3"
                    placeholder="记录技术表现、结论与建议，例如：基础扎实，方案设计清晰，建议进入下一轮"
                  ></textarea>
                </label>

                <div class="iv-ops">
                  <span class="iv-hint">{{ ivHint }}</span>
                  <button class="btn btn-sm" type="submit" :disabled="ivBusy">
                    <AppIcon name="check" :size="14" />{{ ivBusy ? '保存中…' : '保存面试信息' }}
                  </button>
                </div>
              </form>

              <div v-else class="iv-read">
                <div class="iv-read-grid">
                  <div>
                    <span>面试时间</span>
                    <b>{{ ivAt ? fmtInterview(ivAt) : '技术部尚未安排' }}</b>
                  </div>
                  <div>
                    <span>面试形式</span>
                    <b>{{ INTERVIEW_MODE_LABELS[c.interview_mode] || '—' }}</b>
                  </div>
                  <div>
                    <span>面试官</span>
                    <b>{{ c.interviewer || '—' }}</b>
                  </div>
                </div>
                <div class="iv-fb">
                  <span>面试反馈</span>
                  <p>{{ c.interview_feedback || '暂无反馈记录' }}</p>
                </div>
              </div>
            </section>

            <section class="panel resume-card">
              <header class="panel-head">
                <div>
                  <h3 class="panel-title">简历原文</h3>
                  <p class="panel-sub">由 PDF / Word 解析入库</p>
                </div>
                <span class="meta-chip">{{ resumeLength }} 字</span>
              </header>
              <div class="resume-text">{{ c.resume_text || '暂无简历正文。可重新上传附件补充。' }}</div>
            </section>
          </div>

          <aside class="col-side">
            <section class="panel side">
              <h3 class="side-title">招聘阶段</h3>
              <ol class="steps">
                <li v-for="s in steps" :key="s.key" :class="{ current: status === s.key }">
                  <button
                    class="step-btn"
                    type="button"
                    :class="{ locked: status !== s.key && !canMove(role, status, s.key) }"
                    :disabled="statusBusy || status === s.key || !canMove(role, status, s.key)"
                    :aria-current="status === s.key ? 'true' : undefined"
                    :title="status === s.key ? '当前阶段' : stepHint(s.key)"
                    @click="changeStatus(s.key)"
                  >
                    <span class="step-dot" :style="{ '--c': s.color }"></span>
                    <span class="step-label">{{ s.label }}</span>
                    <span v-if="status === s.key" class="step-tag">当前</span>
                    <span v-else-if="!canMove(role, status, s.key)" class="step-owner">
                      {{ OWNER_LABELS[s.owner] }}
                    </span>
                  </button>
                </li>
              </ol>
              <p class="side-note">
                当前由{{ OWNER_LABELS[currentStep.owner] }}推进；{{ nextHint }}
              </p>
              <p v-if="isFinal" class="retention-note">
                <AppIcon name="clock" :size="13" />
                <span>{{ retentionText }}</span>
              </p>
            </section>

            <section class="panel side">
              <h3 class="side-title">档案信息</h3>
              <div class="kv">
                <span>候选人编号</span>
                <b class="mono">#{{ c.id }}</b>
              </div>
              <div class="kv">
                <span>意向岗位</span>
                <b>{{ c.expected_position || '—' }}</b>
              </div>
              <div class="kv">
                <span>招聘阶段</span>
                <b>{{ statusLabel }}</b>
              </div>
              <div class="kv">
                <span>当前环节负责人</span>
                <b>{{ OWNER_LABELS[currentStep.owner] }}</b>
              </div>
              <div class="kv">
                <span>最近操作人</span>
                <b>{{ c.status_changed_by || '—' }}</b>
              </div>
              <div class="kv">
                <span>简历字数</span>
                <b class="mono">{{ resumeLength }}</b>
              </div>
            </section>
          </aside>
        </div>
      </template>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { toast, confirmAction } from '../lib/ui.js'
import { isTech, role, user } from '../lib/auth.js'
import {
  FINAL_STATUSES,
  INTERVIEW_MODES,
  INTERVIEW_MODE_LABELS,
  OWNER_LABELS,
  ROLE_LABELS,
  STEPS as STEPS_SRC,
  STEPS_BY_KEY,
  TECH_VISIBLE,
  canMove as canMoveByRole,
  hasPerm,
  labelOf,
  rolesFor,
  targetsOf,
} from '../lib/flow.js'
import AppShell from '../components/AppShell.vue'
import AppIcon from '../components/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const c = ref(null)
const statusBusy = ref(false)
const loadError = ref('')

const STEPS = STEPS_SRC
const steps = STEPS
const status = computed(() => c.value?.status || 'new')
const currentStep = computed(() => STEPS_BY_KEY[status.value] || STEPS_BY_KEY.new)
const statusLabel = computed(() => currentStep.value.label)
const initial = computed(() => (c.value?.name || '?').trim().slice(0, 1))
const resumeLength = computed(() => (c.value?.resume_text || '').length)

const backPath = computed(() => (isTech.value ? '/kanban' : '/'))
const backLabel = computed(() => (isTech.value ? '返回看板' : '返回工作台'))

// 与后端 db.RETENTION_DAYS 保持一致：终态档案保留 7 天后自动删除
const RETENTION_DAYS = 7
const isFinal = computed(() => FINAL_STATUSES.includes(status.value))

// 当前角色能否推进到目标阶段
function canMove(roleKey, from, to) {
  return canMoveByRole(roleKey, from, to)
}

const nextHint = computed(() => {
  if (isFinal.value) return '流程已结束，档案将在到期后自动清理'
  const targets = targetsOf(role.value, status.value)
  if (!targets.length) {
    return `如需推进，请联系${OWNER_LABELS[currentStep.value.owner]}或管理员`
  }
  return `你可以推进到「${targets.map(labelOf).join('、')}」`
})

function stepHint(key) {
  if (key === status.value) return '当前阶段'
  if (canMoveByRole(role.value, status.value, key)) return `推进到「${labelOf(key)}」`
  const need = rolesFor(status.value, key)
  if (need.length) return `「${labelOf(key)}」需${need.map((r) => ROLE_LABELS[r]).join('、')}操作`
  return `不能从「${labelOf(status.value)}」直接到「${labelOf(key)}」`
}

const daysLeft = computed(() => {
  if (!isFinal.value || !c.value?.status_changed_at) return null
  const at = new Date(String(c.value.status_changed_at).replace(' ', 'T')).getTime()
  if (Number.isNaN(at)) return null
  const left = Math.ceil((at + RETENTION_DAYS * 86400000 - Date.now()) / 86400000)
  return Math.max(0, left)
})

const retentionText = computed(() => {
  if (daysLeft.value === null) return `终态档案保留 ${RETENTION_DAYS} 天，到期自动删除`
  if (daysLeft.value === 0) return '该档案今天将自动删除'
  return `该档案将在 ${daysLeft.value} 天后自动删除`
})

/* --------------------------- 面试安排 --------------------------- */
const ivBusy = ref(false)
const iv = ref({ at: '', mode: 'onsite', interviewer: '', feedback: '' })

const ivAt = computed(() => c.value?.interview_at || '')
const inTechWindow = computed(() => TECH_VISIBLE.includes(status.value))
const hasInterview = computed(() =>
  Boolean(
    ivAt.value ||
      c.value?.interview_mode ||
      c.value?.interviewer ||
      c.value?.interview_feedback,
  ),
)
const showInterview = computed(() => inTechWindow.value || hasInterview.value)
const canEditInterview = computed(
  () => inTechWindow.value && hasPerm(role.value, 'interview.manage'),
)

function toInputValue(v) {
  if (!v) return ''
  return String(v).replace(' ', 'T').slice(0, 16)
}

function fmtInterview(v) {
  if (!v) return '待安排'
  const d = new Date(String(v).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(v).slice(5, 16)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}月${pad(d.getDate())}日 ${pad(d.getHours())}:${pad(
    d.getMinutes(),
  )}`
}

const ivHint = computed(() => {
  if (!iv.value.at) return '填写面试时间后保存，看板卡片会同步显示'
  return `已安排 ${fmtInterview(iv.value.at)}，可随时更新`
})

function syncIv() {
  const cur = c.value || {}
  iv.value = {
    at: toInputValue(cur.interview_at),
    mode: cur.interview_mode || 'onsite',
    interviewer:
      cur.interviewer || (role.value === 'tech' ? user.value.display_name || '' : ''),
    feedback: cur.interview_feedback || '',
  }
}

async function saveInterview() {
  if (ivBusy.value || !c.value) return
  ivBusy.value = true
  try {
    const data = await api.updateInterview(c.value.id, {
      interview_at: iv.value.at || null,
      mode: iv.value.mode || null,
      interviewer: iv.value.interviewer || '',
      feedback: iv.value.feedback || '',
    })
    if (data && data.candidate) c.value = data.candidate
    syncIv()
    toast('面试信息已保存', 'success')
  } catch (e) {
    toast('保存失败：' + e.message, 'error')
  } finally {
    ivBusy.value = false
  }
}

const PALETTE = [
  ['#3f6df0', '#1a3fbd'],
  ['#7c5cf0', '#4a2fb0'],
  ['#12997a', '#07624c'],
  ['#c2811f', '#8a5608'],
  ['#cc4f87', '#93275a'],
  ['#2f8aa8', '#195a70'],
]

const avatarStyle = computed(() => {
  const name = c.value?.name || '?'
  let sum = 0
  for (const ch of name) sum += ch.charCodeAt(0)
  const [a, b] = PALETTE[sum % PALETTE.length]
  return { background: `linear-gradient(145deg, ${a}, ${b})` }
})

const skillList = computed(() =>
  (c.value?.skills || '')
    .split(/[,，、/|]/)
    .map((s) => s.trim())
    .filter(Boolean),
)

async function load() {
  loadError.value = ''
  try {
    const data = await api.candidate(route.params.id)
    c.value = data.candidate
    syncIv()
  } catch (e) {
    loadError.value = e.message || '无法连接服务'
  }
}

async function remove() {
  const ok = await confirmAction({
    title: '删除这位候选人？',
    message: `「${c.value.name}」的档案与简历正文将被永久删除，无法恢复。`,
    confirmText: '删除',
    danger: true,
  })
  if (!ok) return
  try {
    await api.deleteCandidate(c.value.id)
    toast('候选人已删除', 'success')
    router.push('/')
  } catch (e) {
    toast('删除失败：' + e.message, 'error')
  }
}

async function changeStatus(key) {
  if (statusBusy.value || key === status.value) return
  if (!canMoveByRole(role.value, status.value, key)) {
    toast(stepHint(key), 'error')
    return
  }
  const prev = status.value
  statusBusy.value = true
  c.value = { ...c.value, status: key }
  try {
    const data = await api.updateCandidateStatus(c.value.id, key)
    if (data && data.candidate) c.value = data.candidate
    toast(`已移至「${labelOf(key)}」`, 'success')
  } catch (e) {
    c.value = { ...c.value, status: prev }
    toast('阶段更新失败：' + e.message, 'error')
  } finally {
    statusBusy.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.detail-body {
  flex: 1;
  min-height: 0;
  padding-right: 4px;
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

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(260px, 0.8fr);
  gap: 18px;
  align-items: start;
  padding-bottom: 6px;
}

.col-main,
.col-side {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}

/* 档案卡 */
.profile {
  padding: 24px 26px 22px;
}

.profile-top {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--line-soft);
}

.profile-avatar {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  font-size: 23px;
  box-shadow: 0 14px 26px -18px rgba(15, 26, 48, 0.7);
}

.profile-id {
  flex: 1;
  min-width: 0;
}

.profile-id h2 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.25;
}

.profile-id p {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  font-size: 13px;
  color: var(--text-3);
}

.facts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 20px;
  padding: 20px 0 4px;
}

.fact {
  min-width: 0;
}

.fact dt {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--text-3);
}

.fact dt .icon {
  width: 14px;
  height: 14px;
  color: #98a3b8;
}

.fact dd {
  margin-top: 5px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text);
  word-break: break-word;
}

.fact dd a {
  color: var(--brand-strong);
  border-bottom: 1px solid var(--brand-line);
  padding-bottom: 1px;
  transition: color 0.18s;
}

.fact dd a:hover {
  color: var(--brand);
}

.skill-block {
  margin-top: 18px;
  padding-top: 18px;
  border-top: 1px solid var(--line-soft);
}

.skill-block h4,
.side-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--text-3);
  text-transform: uppercase;
}

.skill-block .tags {
  margin-top: 9px;
}

/* 面试安排 */
.iv-flag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}

.iv-flag.set {
  background: var(--violet-soft);
  color: #5a40c4;
}

.iv-flag.unset {
  background: #f1f4fa;
  color: var(--text-3);
}

.iv-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 22px 20px;
}

.iv-row {
  display: grid;
  grid-template-columns: 1.1fr 1.2fr 1fr;
  gap: 14px;
}

.iv-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.iv-field > span {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-2);
}

.iv-seg {
  align-self: flex-start;
}

.iv-seg button {
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
}

.iv-area {
  height: auto;
  padding: 10px 12px;
  font-family: var(--font);
  font-size: 13px;
  line-height: 1.7;
  resize: vertical;
}

.iv-ops {
  display: flex;
  align-items: center;
  gap: 12px;
}

.iv-hint {
  flex: 1;
  font-size: 11.5px;
  color: var(--text-3);
}

.iv-read {
  padding: 16px 22px 20px;
}

.iv-read-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.iv-read-grid span {
  font-size: 11.5px;
  color: var(--text-3);
}

.iv-read-grid b {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.iv-fb {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--line-soft);
}

.iv-fb > span {
  font-size: 11.5px;
  color: var(--text-3);
}

.iv-fb p {
  margin-top: 5px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--text-2);
  white-space: pre-wrap;
}

/* 简历正文 */
.resume-card {
  flex: 1;
}

.meta-chip {
  flex: none;
  padding: 3px 9px;
  border-radius: 999px;
  background: #f1f4fa;
  color: var(--text-3);
  font-family: var(--mono);
  font-size: 11px;
}

.resume-text {
  padding: 22px 26px 26px;
  font-size: 13.5px;
  line-height: 1.95;
  color: var(--text-2);
  white-space: pre-wrap;
  word-break: break-word;
}

/* 侧栏 */
.side {
  padding: 18px 20px;
}

.side-title {
  margin-bottom: 12px;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.steps li {
  display: block;
}

.step-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 9px 10px;
  border-radius: 9px;
  font-size: 13px;
  color: var(--text-3);
  text-align: left;
  transition: background 0.18s, color 0.18s;
}

.step-btn:hover:not(:disabled) {
  background: #f5f7fb;
  color: var(--text-2);
}

.step-btn:disabled {
  cursor: default;
}

.step-btn.locked {
  opacity: 0.55;
}

.step-owner {
  margin-left: auto;
  font-size: 10px;
  color: #a3acbd;
}

.steps li.current .step-btn {
  background: #f4f7ff;
  color: var(--text);
  font-weight: 600;
}

.step-dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 50%;
  background: var(--c);
  opacity: 0.4;
}

.steps li.current .step-dot {
  opacity: 1;
  transform: scale(1.15);
}

.step-tag {
  margin-left: auto;
  padding: 1px 7px;
  border-radius: 5px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 10.5px;
  font-weight: 700;
}

.side-note {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
  font-size: 11.5px;
  line-height: 1.7;
  color: var(--text-3);
}

.retention-note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff8ec;
  font-size: 11.5px;
  line-height: 1.6;
  color: #8a5b12;
}

.kv {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 0;
  border-bottom: 1px solid var(--line-soft);
  font-size: 12.5px;
}

.kv:last-child {
  border-bottom: none;
  padding-bottom: 2px;
}

.kv span {
  color: var(--text-3);
}

.kv b {
  font-weight: 600;
  text-align: right;
}

.mono {
  font-family: var(--mono);
  font-size: 12px;
}

@media (max-width: 1080px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .col-side {
    flex-direction: row;
  }

  .col-side .side {
    flex: 1;
  }

  .iv-row {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 700px) {
  .col-side {
    flex-direction: column;
  }

  .iv-row,
  .iv-read-grid {
    grid-template-columns: 1fr;
  }

  .facts {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .profile {
    padding: 20px 18px;
  }

  .profile-avatar {
    width: 48px;
    height: 48px;
    border-radius: 15px;
    font-size: 19px;
  }

  .profile-id h2 {
    font-size: 20px;
  }

  .profile-top {
    flex-wrap: wrap;
  }

  .resume-text {
    padding: 18px;
  }
}
</style>
