<template>
  <div class="kanban-shell">
    <header class="topbar">
      <span class="brand">候选人看板</span>
      <div class="user">
        <button class="btn btn-ghost" @click="$router.push('/')">返回工作台</button>
      </div>
    </header>

    <div class="board">
      <div
        v-for="col in columns"
        :key="col.key"
        class="col"
        @dragover.prevent
        @drop="onDrop(col.key)"
      >
        <div class="col-head">
          <span class="dot" :style="{ background: col.color }"></span>
          <span class="col-label">{{ col.label }}</span>
          <span class="count">{{ group[col.key].length }}</span>
        </div>
        <div class="col-body" :class="{ over: overCol === col.key }" @dragenter="overCol = col.key" @dragleave="overCol = null">
          <div
            v-for="c in group[col.key]"
            :key="c.id"
            class="kanban-card"
            draggable="true"
            @dragstart="onDragStart(c)"
            @click="$router.push('/candidates/' + c.id)"
          >
            <div class="k-name">{{ c.name }}</div>
            <div class="k-pos">{{ c.expected_position || '未填岗位' }}</div>
            <div class="k-skills">{{ c.skills }}</div>
          </div>
          <p v-if="!group[col.key].length" class="empty">拖拽候选人到此处</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api.js'

const columns = [
  { key: 'new', label: '新简历', color: '#9aa5b1' },
  { key: 'screening', label: '筛选中', color: '#1a6fe0' },
  { key: 'interview', label: '面试中', color: '#9b59b6' },
  { key: 'offered', label: '已通过', color: '#27ae60' },
  { key: 'rejected', label: '已淘汰', color: '#e74c3c' },
]

const candidates = ref([])
const dragging = ref(null)
const overCol = ref(null)

const group = computed(() => {
  const g = {}
  for (const col of columns) g[col.key] = []
  for (const c of candidates.value) {
    const s = c.status || 'new'
    if (g[s]) g[s].push(c)
    else g['new'].push(c)
  }
  return g
})

function onDragStart(c) {
  dragging.value = c
}

async function onDrop(status) {
  overCol.value = null
  const c = dragging.value
  dragging.value = null
  if (!c) return
  if ((c.status || 'new') === status) return
  // 乐观更新：先改本地，失败再回滚
  const prev = c.status || 'new'
  c.status = status
  try {
    await api.updateCandidateStatus(c.id, status)
  } catch (e) {
    c.status = prev
    alert('状态更新失败：' + e.message)
  }
}

async function load() {
  const data = await api.candidates()
  candidates.value = data.candidates
}

onMounted(load)
</script>

<style scoped>
.kanban-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.topbar {
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e5e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.topbar .brand {
  font-size: 18px;
  font-weight: 700;
  color: #1a6fe0;
}

.board {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 16px 24px;
  overflow-x: auto;
  align-items: flex-start;
}

.col {
  flex: 1;
  min-width: 220px;
  background: #fff;
  border: 1px solid #e5e8f0;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 88px);
}

.col-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid #f0f1f6;
  font-size: 14px;
  font-weight: 600;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.count {
  margin-left: auto;
  background: #f0f2f7;
  color: #666;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 10px;
}

.col-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  min-height: 120px;
}

.col-body.over {
  background: #f6f9ff;
}

.kanban-card {
  padding: 10px 12px;
  border: 1px solid #eef0f5;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: grab;
  background: #fff;
  transition: box-shadow 0.15s, transform 0.15s;
}

.kanban-card:hover {
  box-shadow: 0 2px 8px rgba(26, 111, 224, 0.12);
  transform: translateY(-1px);
}

.k-name {
  font-size: 15px;
  font-weight: 600;
}

.k-pos {
  color: #1a6fe0;
  font-size: 13px;
  margin: 3px 0;
}

.k-skills {
  color: #999;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty {
  color: #bbb;
  font-size: 13px;
  text-align: center;
  padding: 24px 0;
}
</style>