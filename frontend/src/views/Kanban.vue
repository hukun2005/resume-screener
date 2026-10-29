<template>
  <AppShell
    kicker="PIPELINE"
    title="候选人看板"
    :subtitle="subtitle"
  >
    <template #actions>
      <div class="head-stat">
        <b>{{ candidates.length }}</b>
        <span>候选人</span>
      </div>
    </template>

    <div v-if="loadError" class="empty-state board-err">
      <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
      <h4>看板加载失败</h4>
      <p>{{ loadError }}</p>
      <button class="btn btn-ghost btn-sm retry-btn" @click="load">
        <AppIcon name="refresh" :size="14" />重新加载
      </button>
    </div>

    <div v-else class="board">
      <section
        v-for="col in columns"
        :key="col.key"
        class="column"
        :style="{ '--dot': col.color, '--tint': col.tint }"
        @dragover.prevent
        @drop="onDrop(col.key)"
      >
        <header class="col-head">
          <span class="col-dot"></span>
          <h3>{{ col.label }}</h3>
          <span class="col-owner">{{ OWNER_LABELS[col.owner] }}</span>
          <span class="count">{{ group[col.key].length }}</span>
        </header>

        <div
          class="col-body scroll"
          :class="{ over: overCol === col.key }"
          @dragover.prevent
          @dragenter="overCol = col.key"
          @dragleave="overCol = null"
        >
          <article
            v-for="c in group[col.key]"
            :key="c.id"
            class="k-card"
            draggable="true"
            tabindex="0"
            role="button"
            :aria-label="`${c.name} · ${col.label}，打开详情`"
            :class="{ dragging: dragging && dragging.id === c.id }"
            @dragstart="onDragStart(c)"
            @dragend="onDragEnd"
            @click="open(c)"
            @keydown.enter.prevent="open(c)"
            @keydown.space.prevent="open(c)"
          >
            <div class="k-top">
              <span class="k-avatar">{{ (c.name || '?').slice(0, 1) }}</span>
              <span class="k-name">{{ c.name }}</span>
            </div>
            <p class="k-pos">{{ c.expected_position || '未填岗位' }}</p>
            <p v-if="c.skills" class="k-skills">{{ c.skills }}</p>
            <p v-if="c.interview_at" class="k-iv">
              <AppIcon name="clock" :size="11" />
              <span>{{ ivLine(c) }}</span>
            </p>
          </article>

          <p v-if="!group[col.key].length" class="col-empty">
            {{ col.key === 'new' ? '新简历会自动进入此列' : '暂无候选人' }}
          </p>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { toast } from '../lib/ui.js'
import { role, roleLabel } from '../lib/auth.js'
import { OWNER_LABELS, ROLE_LABELS, STEPS, TECH_VISIBLE, INTERVIEW_MODE_LABELS, canMove, canViewAll, labelOf, rolesFor } from '../lib/flow.js'
import AppShell from '../components/AppShell.vue'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()

// 没有「查看全部候选人」权限时只显示已推送的三个阶段
const columns = computed(() =>
  canViewAll(role.value) ? STEPS : STEPS.filter((s) => TECH_VISIBLE.includes(s.key)),
)

const subtitle = computed(() =>
  canViewAll(role.value)
    ? `当前角色：${roleLabel.value}。HR 负责初筛与推送，技术部负责约面与面试结论，面试通过后由 HR 发 offer；已通过 / 已淘汰的档案保留 7 天后自动删除`
    : 'HR 推送过来的候选人在此处理：约面试、判定面试结果；通过后由 HR 决定是否发 offer',
)

const candidates = ref([])
const dragging = ref(null)
const overCol = ref(null)
const loadError = ref('')

const group = computed(() => {
  const g = {}
  for (const col of columns.value) g[col.key] = []
  for (const c of candidates.value) {
    const s = c.status || 'new'
    if (g[s]) g[s].push(c)
  }
  return g
})

function open(c) {
  router.push('/candidates/' + c.id)
}

// 卡片上的面试时间：10-31 10:30 · 现场
function ivLine(c) {
  const d = new Date(String(c.interview_at).replace(' ', 'T'))
  const mode = INTERVIEW_MODE_LABELS[c.interview_mode]
  if (Number.isNaN(d.getTime())) return mode || '已安排面试'
  const pad = (n) => String(n).padStart(2, '0')
  const when = `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes(),
  )}`
  return mode ? `${when} · ${mode}` : when
}

function onDragStart(c) {
  dragging.value = c
}

function onDragEnd() {
  dragging.value = null
  overCol.value = null
}

async function onDrop(status) {
  overCol.value = null
  const c = dragging.value
  dragging.value = null
  if (!c) return
  const from = c.status || 'new'
  if (from === status) return
  if (!canMove(role.value, from, status)) {
    const need = rolesFor(from, status)
    toast(
      need.length
        ? `「${labelOf(from)}」→「${labelOf(status)}」需要${need.map((r) => ROLE_LABELS[r]).join('、')}权限`
        : `「${labelOf(from)}」不能直接流转到「${labelOf(status)}」`,
      'error',
    )
    return
  }
  // 乐观更新：先改本地，失败再回滚
  c.status = status
  try {
    await api.updateCandidateStatus(c.id, status)
    toast(`${c.name} 已移至「${labelOf(status)}」`, 'success')
  } catch (e) {
    c.status = from
    toast('状态更新失败：' + e.message, 'error')
  }
}

async function load() {
  loadError.value = ''
  try {
    const data = await api.candidates()
    candidates.value = data.candidates
  } catch (e) {
    loadError.value = e.message || '无法连接服务'
  }
}

onMounted(load)
</script>

<style scoped>
.head-stat {
  display: flex;
  align-items: baseline;
  gap: 7px;
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shadow-xs);
}

.head-stat b {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.head-stat span {
  font-size: 11px;
  color: var(--text-3);
}

.board {
  display: flex;
  flex: 1;
  gap: 16px;
  min-height: 0;
  padding-bottom: 6px;
  overflow-x: auto;
  align-items: stretch;
}

.board::-webkit-scrollbar {
  height: 10px;
}

.board::-webkit-scrollbar-thumb {
  border: 3px solid transparent;
  border-radius: 10px;
  background: #d5dbe7;
  background-clip: content-box;
}

.column {
  display: flex;
  flex-direction: column;
  flex: 1 0 214px;
  min-width: 210px;
  max-width: 320px;
  min-height: 0;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #f7f8fc;
  overflow: hidden;
}

.col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background: var(--tint);
  border-bottom: 1px solid rgba(15, 26, 48, 0.05);
}

.col-dot {
  width: 8px;
  height: 8px;
  flex: none;
  border-radius: 50%;
  background: var(--dot);
}

.col-head h3 {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.col-owner {
  padding: 1px 6px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.75);
  color: var(--text-3);
  font-size: 10px;
  font-weight: 600;
}

.count {
  margin-left: auto;
  min-width: 22px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  color: var(--text-2);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  text-align: center;
}

.col-body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  min-height: 140px;
  padding: 10px;
  transition: background 0.18s, box-shadow 0.18s;
}

.col-body.over {
  background: var(--tint);
  box-shadow: inset 0 0 0 2px var(--dot);
}

.k-card {
  padding: 11px 12px;
  border: 1px solid #e8ecf4;
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shadow-xs);
  cursor: grab;
  transition: box-shadow 0.16s, transform 0.16s, border-color 0.16s;
}

.k-card:hover {
  border-color: #d3dbe9;
  box-shadow: 0 10px 22px -16px rgba(15, 26, 48, 0.6);
  transform: translateY(-1px);
}

.k-card:active {
  cursor: grabbing;
}

.k-card:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}

.board-err {
  flex: 1;
  justify-content: center;
  border: 1px solid var(--line);
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

.k-card.dragging {
  opacity: 0.5;
  transform: rotate(-1.2deg) scale(0.99);
  box-shadow: var(--shadow);
}

.k-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.k-avatar {
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

.k-name {
  font-size: 13.5px;
  font-weight: 600;
  letter-spacing: -0.01em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.k-pos {
  margin-top: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--brand-strong);
}

.k-skills {
  margin-top: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  color: var(--text-3);
}

.k-iv {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 7px;
  padding: 3px 8px;
  border-radius: 7px;
  background: #f4f1fe;
  color: #5a40c4;
  font-size: 11px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.k-iv .icon {
  flex: none;
}

.col-empty {
  padding: 20px 8px;
  border: 1px dashed #d8dfec;
  border-radius: 10px;
  text-align: center;
  font-size: 11.5px;
  color: #a3acbd;
}

@media (max-width: 760px) {
  .head-stat {
    display: none;
  }

  .board {
    gap: 12px;
    padding-bottom: 10px;
  }

  .column {
    flex: 0 0 230px;
  }
}
</style>
