<template>
  <AppShell
    kicker="INTERVIEWS"
    title="面试管理"
    :subtitle="subtitle"
  >
    <template #actions>
      <span class="head-count">
        共 <b>{{ list.length }}</b> 位
      </span>
      <button class="btn btn-ghost btn-sm refresh-btn" :disabled="loading" @click="load">
        <AppIcon name="refresh" :size="14" />{{ loading ? '刷新中…' : '刷新' }}
      </button>
    </template>

    <div class="iv-wrap">
      <!-- 分段统计 -->
      <section class="iv-stats">
        <button
          v-for="s in SEGMENTS"
          :key="s.key"
          type="button"
          class="stat"
          :class="{ active: seg === s.key }"
          :style="{ '--accent': s.color, '--soft': s.tint }"
          :aria-pressed="seg === s.key"
          @click="seg = s.key"
        >
          <span class="stat-label">{{ s.label }}</span>
          <b>{{ counts[s.key] }}</b>
          <small>{{ s.hint }}</small>
        </button>
      </section>

      <!-- 搜索 -->
      <div class="iv-tools">
        <label class="search">
          <AppIcon name="search" :size="15" />
          <input v-model="q" placeholder="搜索候选人 / 岗位 / 面试官 / 反馈" autocomplete="off" />
        </label>
        <span class="stage-chip">{{ segLabel }} · {{ list.length }} 位</span>
      </div>

      <div v-if="loadError" class="empty-state iv-empty">
        <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
        <h4>面试数据加载失败</h4>
        <p>{{ loadError }}</p>
        <button class="btn btn-ghost btn-sm retry-btn" @click="load">
          <AppIcon name="refresh" :size="14" />重新加载
        </button>
      </div>

      <div v-else-if="loading" class="iv-list scroll">
        <div v-for="i in 4" :key="i" class="iv-skeleton"></div>
      </div>

      <div v-else-if="list.length" class="iv-list scroll">
        <article
          v-for="c in list"
          :key="c.id"
          class="iv-card"
          :class="{ today: isToday(c.interview_at), overdue: isOverdue(c) }"
          tabindex="0"
          role="button"
          :aria-label="`${c.name} 的面试，打开详情`"
          @click="open(c)"
          @keydown.enter.prevent="open(c)"
          @keydown.space.prevent="open(c)"
        >
          <div class="iv-when">
            <template v-if="whenOf(c)">
              <b>{{ whenOf(c).md }}</b>
              <span>{{ whenOf(c).time }}</span>
              <small>{{ whenOf(c).rel }}</small>
            </template>
            <template v-else>
              <span class="no-time">待安排</span>
              <small>{{ isTechStage(c) ? '尚未约面' : '未进入面试' }}</small>
            </template>
          </div>

          <div class="iv-main">
            <div class="iv-top">
              <span class="iv-avatar">{{ (c.name || '?').slice(0, 1) }}</span>
              <div class="iv-title">
                <b>{{ c.name }}</b>
                <small>{{ c.expected_position || '未填岗位' }}</small>
              </div>
              <span class="st-chip" :style="chipStyle(c.status)">
                {{ labelOf(c.status) }}
              </span>
            </div>

            <div class="iv-meta">
              <span class="meta">
                <AppIcon name="user" :size="12" />
                {{ c.interviewer || '未填写面试官' }}
              </span>
              <span v-if="c.interview_at && c.interview_mode" class="meta">
                {{ INTERVIEW_MODE_LABELS[c.interview_mode] || c.interview_mode }}
              </span>
              <span v-if="isOverdue(c)" class="meta warn">
                <AppIcon name="alert" :size="12" />待反馈
              </span>
            </div>

            <p v-if="c.interview_feedback" class="iv-fb">
              <em>面试反馈</em>{{ c.interview_feedback }}
            </p>
            <p v-else-if="bucketOf(c) === 'pending'" class="iv-fb faded">
              面试时间已到，尚未填写反馈
            </p>
          </div>

          <span class="iv-go"><AppIcon name="chevronRight" :size="16" /></span>
        </article>
      </div>

      <div v-else class="empty-state iv-empty">
        <span class="empty-ico"><AppIcon name="clock" :size="22" /></span>
        <h4>{{ emptyTitle }}</h4>
        <p>{{ emptyHint }}</p>
        <button v-if="q" class="btn btn-ghost btn-sm retry-btn" @click="q = ''">清除搜索</button>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import {
  INTERVIEW_MODE_LABELS,
  STEPS_BY_KEY,
  labelOf,
} from '../lib/flow.js'
import AppShell from '../components/AppShell.vue'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()

const SEGMENTS = [
  { key: 'all', label: '全部', hint: '所有可见候选人', color: '#2456e6', tint: '#eaf0ff' },
  { key: 'todo', label: '待约面', hint: '已推送，尚未安排时间', color: '#2f8aa8', tint: '#e8f4f8' },
  { key: 'upcoming', label: '待面试', hint: '已安排，尚未到时间', color: '#6c52d4', tint: '#efecfd' },
  { key: 'pending', label: '待反馈', hint: '已到时间，等待结果', color: '#c2811f', tint: '#fdf5e6' },
  { key: 'done', label: '已结束', hint: '面试已出结论', color: '#0f8a68', tint: '#e6f6f0' },
]

const candidates = ref([])
const loading = ref(true)
const loadError = ref('')
const seg = ref('upcoming')
const q = ref('')

/* ---------------- 数据 ---------------- */
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = await api.candidates()
    candidates.value = data.candidates || []
  } catch (e) {
    loadError.value = e.message || '无法连接服务'
  } finally {
    loading.value = false
  }
}

// 兼容 "2026-10-31T10:30:00" 与 "2026/10/31 10:30:00"
function parseAt(v) {
  if (!v) return null
  const s = String(v).trim().replace(/\//g, '-').replace(' ', 'T')
  const d = new Date(s)
  return Number.isNaN(d.getTime()) ? null : d
}

function timeVal(c) {
  const d = parseAt(c.interview_at)
  return d ? d.getTime() : null
}

function bucketOf(c) {
  const s = c.status || 'new'
  if (s === 'tech_review') return 'todo'
  if (s === 'interview') {
    const t = timeVal(c)
    return t && t > Date.now() ? 'upcoming' : 'pending'
  }
  if (s === 'tech_passed' || s === 'offered' || s === 'rejected') return 'done'
  return 'other'
}

const counts = computed(() => {
  const n = { all: candidates.value.length, todo: 0, upcoming: 0, pending: 0, done: 0 }
  for (const c of candidates.value) {
    const b = bucketOf(c)
    if (n[b] != null) n[b] += 1
  }
  return n
})

const segLabel = computed(() => SEGMENTS.find((s) => s.key === seg.value)?.label || '全部')

const list = computed(() => {
  const kw = q.value.trim().toLowerCase()
  let arr = candidates.value.filter((c) => seg.value === 'all' || bucketOf(c) === seg.value)
  if (kw) {
    arr = arr.filter((c) =>
      [c.name, c.expected_position, c.interviewer, c.interview_feedback]
        .join(' ')
        .toLowerCase()
        .includes(kw),
    )
  }
  return sortList(arr.slice())
})

function sortList(arr) {
  const rank = { upcoming: 0, pending: 1, todo: 2, done: 3, other: 4 }
  const byTime = (a, b, dir) => {
    const ta = timeVal(a)
    const tb = timeVal(b)
    if (ta == null && tb == null) return b.id - a.id
    if (ta == null) return 1
    if (tb == null) return -1
    return dir * (ta - tb)
  }
  if (seg.value === 'upcoming' || seg.value === 'pending') return arr.sort((a, b) => byTime(a, b, 1))
  if (seg.value === 'done') return arr.sort((a, b) => byTime(a, b, -1))
  if (seg.value === 'todo') return arr.sort((a, b) => b.id - a.id)
  return arr.sort(
    (a, b) => rank[bucketOf(a)] - rank[bucketOf(b)] || byTime(a, b, 1),
  )
}

const subtitle = computed(() =>
  loading.value
    ? '集中查看与管理面试安排'
    : `${candidates.value.length} 位候选人进入流程 · 待面试 ${counts.value.upcoming} · 待反馈 ${counts.value.pending}`,
)

const emptyTitle = computed(() => {
  if (q.value) return '没有匹配的候选人'
  return {
    all: '暂无候选人',
    todo: '暂无待约面的候选人',
    upcoming: '暂无即将开始的面试',
    pending: '暂无待反馈的面试',
    done: '还没有已结束的面试',
  }[seg.value]
})

const emptyHint = computed(() => {
  if (q.value) return '换个关键词试试，或清除搜索后查看全部。'
  return {
    all: '简历进入流程后会自动出现在这里。',
    todo: '在候选人看板或详情页为已推送的候选人安排面试时间。',
    upcoming: '安排面试时间后，未到点的面试会集中显示在这里。',
    pending: '面试时间已过的候选人会移到这里，等待填写面试反馈。',
    done: '面试通过、发放 offer 或淘汰后会显示在这里。',
  }[seg.value]
})

/* ---------------- 展示 ---------------- */
function open(c) {
  router.push('/candidates/' + c.id)
}

function isTechStage(c) {
  return c.status === 'tech_review' || c.status === 'interview'
}

function isOverdue(c) {
  return bucketOf(c) === 'pending' && !!parseAt(c.interview_at)
}

function isToday(v) {
  const d = parseAt(v)
  if (!d) return false
  const n = new Date()
  return (
    d.getFullYear() === n.getFullYear() &&
    d.getMonth() === n.getMonth() &&
    d.getDate() === n.getDate()
  )
}

// 日期块：11-02 / 10:30 / 今天|明天|3 天后|已过 2 天
function whenOf(c) {
  const d = parseAt(c.interview_at)
  if (!d) return null
  const pad = (n) => String(n).padStart(2, '0')
  return {
    md: `${pad(d.getMonth() + 1)}-${pad(d.getDate())}`,
    time: `${pad(d.getHours())}:${pad(d.getMinutes())}`,
    rel: relDay(d),
  }
}

function relDay(d) {
  const today = new Date()
  const start = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((start(d) - start(today)) / 86400000)
  if (days === 0) return '今天'
  if (days === 1) return '明天'
  if (days > 1) return `${days} 天后`
  return `已过 ${Math.abs(days)} 天`
}

function chipStyle(status) {
  const s = STEPS_BY_KEY[status] || STEPS_BY_KEY.new
  return { color: s.color, background: s.tint }
}

onMounted(load)
</script>

<style scoped>
.iv-wrap {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
}

.head-count {
  font-size: 12px;
  color: var(--text-3);
}

.head-count b {
  font-size: 15px;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

.refresh-btn {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
}

/* ---------------- 分段统计 ---------------- */
.iv-stats {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  flex: none;
}

.stat {
  --accent: var(--brand);
  --soft: var(--brand-soft);
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-areas:
    'label num'
    'hint hint';
  row-gap: 2px;
  padding: 10px 13px 11px;
  text-align: left;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
}

.stat:hover {
  border-color: var(--accent);
}

.stat.active {
  border-color: var(--accent);
  background: var(--soft);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 12%, transparent);
}

.stat-label {
  grid-area: label;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-2);
}

.stat b {
  grid-area: num;
  font-size: 19px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  color: var(--accent);
}

.stat small {
  grid-area: hint;
  font-size: 10px;
  line-height: 1.5;
  color: var(--text-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---------------- 工具条 ---------------- */
.iv-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.search {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 34px;
  width: 300px;
  max-width: 100%;
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

.search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: none;
  font-size: 12.5px;
  color: var(--text);
}

.stage-chip {
  margin-left: auto;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f4f9;
  color: var(--text-3);
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* ---------------- 列表 ---------------- */
.iv-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 10px;
  flex: 1;
  min-height: 0;
  padding-bottom: 6px;
  overflow-y: auto;
}

.iv-card {
  position: relative;
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr) 20px;
  gap: 12px;
  align-items: center;
  padding: 14px 14px 13px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--shadow-xs);
  cursor: pointer;
  transition: border-color 0.16s, box-shadow 0.16s, transform 0.14s;
}

.iv-card:hover {
  border-color: #cbd5e7;
  box-shadow: 0 12px 26px -20px rgba(15, 26, 48, 0.65);
  transform: translateY(-1px);
}

.iv-card:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}

.iv-card.today {
  border-color: #cfd9f5;
  background: linear-gradient(180deg, #fbfcff, #fff 46%);
}

.iv-card.today::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--brand);
}

.iv-card.overdue::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #c2811f;
}

.iv-when {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  min-height: 62px;
  padding: 6px 4px;
  border-radius: 10px;
  background: #f6f8fd;
}

.iv-card.overdue .iv-when {
  background: #fdf5e6;
}

.iv-when b {
  font-family: var(--mono);
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text);
}

.iv-when span {
  font-family: var(--mono);
  font-size: 12.5px;
  font-weight: 600;
  color: var(--brand-strong);
}

.iv-when small {
  margin-top: 2px;
  font-size: 10px;
  color: var(--text-3);
}

.iv-card.overdue .iv-when small {
  color: #96601a;
  font-weight: 600;
}

.iv-when .no-time {
  font-size: 12px;
  color: var(--text-3);
  font-weight: 600;
}

.iv-main {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.iv-top {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.iv-avatar {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  flex: none;
  border-radius: 8px;
  background: #eef1f8;
  color: #5b6679;
  font-size: 11.5px;
  font-weight: 700;
}

.iv-title {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  flex: 1;
}

.iv-title b {
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.iv-title small {
  font-size: 11px;
  color: var(--brand-strong);
  font-weight: 600;
}

.st-chip {
  flex: none;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  white-space: nowrap;
}

.iv-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 12px;
}

.meta {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-3);
}

.meta .icon {
  flex: none;
}

.meta.warn {
  color: #96601a;
  font-weight: 600;
}

.iv-fb {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--text-2);
}

.iv-fb em {
  margin-right: 6px;
  padding: 1px 6px;
  border-radius: 5px;
  background: #f1f4f9;
  color: var(--text-3);
  font-size: 10px;
  font-style: normal;
  font-weight: 600;
}

.iv-fb.faded {
  color: var(--text-3);
  font-style: italic;
}

.iv-go {
  display: grid;
  place-items: center;
  color: #b9c2d4;
  transition: color 0.16s, transform 0.16s;
}

.iv-card:hover .iv-go {
  color: var(--brand);
  transform: translateX(1px);
}

.iv-skeleton {
  height: 92px;
  border-radius: 14px;
  background: linear-gradient(90deg, #f3f5fa, #eceff6, #f3f5fa);
  background-size: 200% 100%;
  animation: shimmer 1.4s linear infinite;
}

.iv-empty {
  flex: 1;
  justify-content: center;
  border: 1px dashed var(--line);
  border-radius: var(--radius-lg);
  background: #fff;
}

.empty-ico.err {
  background: var(--red-soft);
  color: var(--red);
}

.retry-btn {
  margin-top: 10px;
}

@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

@media (max-width: 1180px) {
  .iv-list {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .iv-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .stat small {
    display: none;
  }
}

@media (max-width: 760px) {
  .iv-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .search {
    width: 100%;
  }

  .stage-chip {
    display: none;
  }
}
</style>
