<template>
  <AppShell
    kicker="WORKSPACE"
    title="AI 招聘工作台"
    subtitle="用自然语言描述用人需求，AI 会检索简历库并给出匹配理由"
  >
    <template #actions>
      <div class="head-stats">
        <div class="stat">
          <b>{{ allCandidates.length }}</b>
          <span>简历库</span>
        </div>
        <div class="stat">
          <b>{{ recommendations.length }}</b>
          <span>推荐记录</span>
        </div>
      </div>
    </template>

    <div class="workbench">
      <AgentChat @result="onResult" />

      <section class="panel results">
        <header class="panel-head results-head">
          <div>
            <h2 class="panel-title">候选人池</h2>
            <p class="panel-sub">{{ tabSub }}</p>
          </div>
          <div
            ref="tablist"
            class="seg"
            role="tablist"
            aria-label="候选人视图"
            @keydown="onTabKey"
          >
            <button
              role="tab"
              :aria-selected="tab === 'recommend'"
              :tabindex="tab === 'recommend' ? 0 : -1"
              :class="{ active: tab === 'recommend' }"
              @click="tab = 'recommend'"
            >
              AI 推荐
            </button>
            <button
              role="tab"
              :aria-selected="tab === 'all'"
              :tabindex="tab === 'all' ? 0 : -1"
              :class="{ active: tab === 'all' }"
              @click="tab = 'all'"
            >
              简历库
            </button>
            <button
              role="tab"
              :aria-selected="tab === 'sent'"
              :tabindex="tab === 'sent' ? 0 : -1"
              :class="{ active: tab === 'sent' }"
              @click="tab = 'sent'"
            >
              已推荐
            </button>
          </div>
        </header>

        <div class="sync-bar">
          <span class="sync-dot" :class="syncTone"></span>
          <span class="sync-msg" :class="{ err: syncError }">{{ syncMsg || '正在读取邮箱同步状态…' }}</span>
          <div class="sync-actions">
            <button v-if="isAdmin" class="btn btn-ghost btn-sm" @click="showEmailConfig = true">
              <AppIcon name="mail" :size="14" />邮箱配置
            </button>
            <button class="btn btn-ghost btn-sm" :disabled="syncing" @click="syncEmail">
              <AppIcon name="sync" :size="14" :class="{ spin: syncing }" />
              {{ syncing ? '同步中…' : '立即同步' }}
            </button>
          </div>
        </div>

        <div class="list scroll">
          <!-- AI 推荐 -->
          <template v-if="tab === 'recommend'">
            <div v-if="!recommendList.length" class="empty-state">
              <span class="empty-ico"><AppIcon name="spark" :size="22" /></span>
              <h4>还没有推荐结果</h4>
              <p>在左侧告诉 AI 你的用人需求，例如「找 3 个会 Python 的前端」，匹配的候选人会出现在这里。</p>
            </div>
            <CandidateCard v-for="c in recommendList" :key="c.id" :c="c" @click="goDetail(c.id)" />
          </template>

          <!-- 简历库 -->
          <template v-else-if="tab === 'all'">
            <div class="tools">
              <div class="tool-block">
                <p class="tool-label"><AppIcon name="upload" :size="13" />上传解析</p>
                <div class="tool-row">
                  <input v-model="upName" class="input" placeholder="候选人姓名" />
                  <input v-model="upPosition" class="input" placeholder="意向岗位（可选）" />
                  <label class="file-pick">
                    <AppIcon name="file" :size="15" />
                    <span>{{ upFile ? upFile.name : '选择 PDF / Word 简历' }}</span>
                    <input type="file" accept=".pdf,.docx,.doc,.txt" @change="onFile" />
                  </label>
                  <button class="btn" :disabled="uploading" @click="doUpload">
                    {{ uploading ? '解析中…' : '上传' }}
                  </button>
                </div>
                <p v-if="upMsg" class="notice">{{ upMsg }}</p>
              </div>

              <div class="tool-block">
                <p class="tool-label"><AppIcon name="filter" :size="13" />结构化筛选</p>
                <div class="tool-row">
                  <input v-model="filter.position" class="input" placeholder="岗位，如 前端" />
                  <input v-model="filter.skills" class="input" placeholder="技能，如 Vue" />
                  <input v-model="filter.education" class="input" placeholder="学历，如 本科" />
                  <input
                    v-model.number="filter.minYears"
                    type="number"
                    class="input"
                    placeholder="最低年限"
                  />
                  <button class="btn btn-soft" @click="applyFilter">筛选</button>
                  <button class="btn btn-ghost" @click="resetFilter">重置</button>
                </div>
              </div>
            </div>

            <template v-if="loadingList">
              <div v-for="n in 3" :key="n" class="sk-card">
                <span class="sk-avatar"></span>
                <div class="sk-lines">
                  <span class="sk-line" style="width: 46%"></span>
                  <span class="sk-line" style="width: 72%"></span>
                  <span class="sk-line" style="width: 30%"></span>
                </div>
              </div>
            </template>

            <div v-else-if="listError" class="empty-state">
              <span class="empty-ico err"><AppIcon name="alert" :size="22" /></span>
              <h4>简历库加载失败</h4>
              <p>{{ listError }}</p>
              <button class="btn btn-ghost btn-sm retry-btn" @click="loadAll">
                <AppIcon name="refresh" :size="14" />重新加载
              </button>
            </div>

            <template v-else>
              <p class="result-meta">{{ allCandidates.length }} 位候选人</p>

              <CandidateCard v-for="c in allCandidates" :key="c.id" :c="c" @click="goDetail(c.id)" />

              <div v-if="!allCandidates.length" class="empty-state">
                <span class="empty-ico"><AppIcon name="inbox" :size="22" /></span>
                <h4>没有符合条件的候选人</h4>
                <p>换个筛选条件试试，或上传一份 PDF / Word 简历，也可以绑定邮箱让招聘邮件自动入库。</p>
              </div>
            </template>
          </template>

          <!-- 已推荐 -->
          <template v-else>
            <div v-if="!recommendations.length" class="empty-state">
              <span class="empty-ico"><AppIcon name="clock" :size="22" /></span>
              <h4>暂无推荐记录</h4>
              <p>AI 每推荐一次候选人，就会在这里留下记录。</p>
            </div>
            <article
              v-for="r in recommendations"
              :key="r.id"
              class="rec-row"
              tabindex="0"
              @click="goDetail(r.candidate_id)"
              @keydown.enter="goDetail(r.candidate_id)"
            >
              <span class="avatar rec-avatar">{{ (r.candidate_name || '?').slice(0, 1) }}</span>
              <div class="rec-main">
                <div class="rec-top">
                  <b>{{ r.candidate_name }}</b>
                  <span class="rec-score">{{ r.match_score }}%</span>
                </div>
                <p>{{ r.requirement }}</p>
              </div>
              <AppIcon name="chevronRight" :size="16" class="rec-go" />
            </article>
          </template>
        </div>
      </section>
    </div>

    <EmailConfigModal v-if="showEmailConfig" @close="showEmailConfig = false" @saved="onEmailSaved" />
  </AppShell>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { toast } from '../lib/ui.js'
import { isAdmin } from '../lib/auth.js'
import AppShell from '../components/AppShell.vue'
import AppIcon from '../components/AppIcon.vue'
import AgentChat from '../components/AgentChat.vue'
import CandidateCard from '../components/CandidateCard.vue'
import EmailConfigModal from '../components/EmailConfigModal.vue'

const router = useRouter()
const tab = ref('recommend')
const TABS = ['recommend', 'all', 'sent']
const tablist = ref(null)
const recommendList = ref([])
const allCandidates = ref([])
const recommendations = ref([])
const loadingList = ref(false)
const listError = ref('')

const upName = ref('')
const upPosition = ref('')
const upFile = ref(null)
const uploading = ref(false)
const upMsg = ref('')
const filter = ref({ position: '', skills: '', education: '', minYears: '' })

const syncing = ref(false)
const syncMsg = ref('')
const syncError = ref(false)
const showEmailConfig = ref(false)

const tabSub = computed(() => {
  if (tab.value === 'recommend') return '来自 AI 的实时语义推荐'
  if (tab.value === 'all') return '全部已入库简历，支持结构化筛选'
  return '历史推荐记录'
})

const syncTone = computed(() => {
  if (syncError.value) return 'err'
  if (syncing.value) return 'busy'
  return 'ok'
})

function onEmailSaved() {
  showEmailConfig.value = false
  toast('邮箱配置已保存', 'success')
  loadEmailStatus()
}

function onTabKey(e) {
  const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
  if (!step) return
  e.preventDefault()
  const i = TABS.indexOf(tab.value)
  tab.value = TABS[(i + step + TABS.length) % TABS.length]
  nextTick(() => {
    const el = tablist.value && tablist.value.querySelector('[aria-selected="true"]')
    if (el) el.focus()
  })
}

async function syncEmail() {
  if (syncing.value) return
  syncing.value = true
  syncMsg.value = '正在连接邮箱拉取简历…'
  syncError.value = false
  try {
    const r = await api.syncEmail()
    syncMsg.value =
      `同步完成：新增 ${r.ingested} 份，重复 ${r.duplicate} 份，` +
      `已处理跳过 ${r.skipped} 份，失败 ${r.failed} 份`
    if (r.ingested > 0) {
      toast(`同步完成，新增 ${r.ingested} 份简历`, 'success')
      await loadAll()
    } else {
      toast('同步完成，没有新的简历', 'info')
    }
  } catch (e) {
    syncError.value = true
    syncMsg.value = '同步失败：' + e.message
    toast('同步失败：' + e.message, 'error')
  } finally {
    syncing.value = false
  }
}

async function loadEmailStatus() {
  try {
    const s = await api.emailStatus()
    if (!s.configured) {
      syncMsg.value = '未绑定邮箱，点击「邮箱配置」完成绑定后自动同步'
    } else if (s.poll_interval > 0) {
      syncMsg.value = `邮箱自动同步已开启（每 ${s.poll_interval} 秒）`
    } else {
      syncMsg.value = '邮箱已配置，需手动同步'
    }
  } catch (e) {
    syncMsg.value = ''
  }
}

function onFile(e) {
  upFile.value = e.target.files[0] || null
}

async function doUpload() {
  if (!upName.value.trim()) {
    upMsg.value = '请先填写候选人姓名'
    return
  }
  if (!upFile.value) {
    upMsg.value = '请先选择简历文件'
    return
  }
  const fd = new FormData()
  fd.append('name', upName.value.trim())
  fd.append('expected_position', upPosition.value.trim())
  fd.append('file', upFile.value)
  uploading.value = true
  upMsg.value = ''
  try {
    await api.uploadCandidate(fd)
    upName.value = ''
    upPosition.value = ''
    upFile.value = null
    upMsg.value = '上传解析成功，已入库'
    toast('简历已解析入库', 'success')
    await loadAll()
  } catch (e) {
    upMsg.value = '上传失败：' + e.message
    toast('上传失败：' + e.message, 'error')
  } finally {
    uploading.value = false
  }
}

function onResult(toolTrace) {
  const hit = toolTrace.find((t) => t.tool === 'search_candidates')
  if (hit && Array.isArray(hit.result)) {
    recommendList.value = hit.result
    tab.value = 'recommend'
  }
  loadRecommendations()
}

async function loadAll() {
  loadingList.value = true
  listError.value = ''
  try {
    const data = await api.candidates({
      position: filter.value.position,
      skills: filter.value.skills,
      education: filter.value.education,
      min_years: filter.value.minYears,
    })
    allCandidates.value = data.candidates
  } catch (e) {
    listError.value = e.message || '无法连接服务'
  } finally {
    loadingList.value = false
  }
}

function applyFilter() {
  loadAll()
}

function resetFilter() {
  filter.value = { position: '', skills: '', education: '', minYears: '' }
  loadAll()
}

async function loadRecommendations() {
  try {
    const data = await api.recommendations()
    recommendations.value = data.recommendations
  } catch (e) {
    toast('推荐记录加载失败：' + e.message, 'error')
  }
}

function goDetail(id) {
  router.push('/candidates/' + id)
}

onMounted(() => {
  loadAll()
  loadRecommendations()
  loadEmailStatus()
})
</script>

<style scoped>
.head-stats {
  display: flex;
  gap: 10px;
}

.stat {
  min-width: 82px;
  padding: 7px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  text-align: center;
  box-shadow: var(--shadow-xs);
}

.stat b {
  display: block;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.stat span {
  font-size: 11px;
  color: var(--text-3);
}

.workbench {
  display: grid;
  grid-template-columns: minmax(340px, 0.92fr) minmax(440px, 1.08fr);
  gap: 18px;
  flex: 1;
  min-height: 0;
}

.results {
  min-height: 0;
}

.results-head {
  flex-wrap: wrap;
}

/* 同步条 */
.sync-bar {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 16px;
  border-bottom: 1px solid var(--line-soft);
  background: #fafbfe;
}

.sync-dot {
  width: 7px;
  height: 7px;
  flex: none;
  border-radius: 50%;
  background: #b8c0d0;
}

.sync-dot.ok {
  background: var(--green);
  box-shadow: 0 0 0 3px rgba(15, 138, 104, 0.13);
}

.sync-dot.busy {
  background: var(--amber);
  box-shadow: 0 0 0 3px rgba(176, 109, 19, 0.14);
  animation: pulse-soft 1.2s ease-in-out infinite;
}

.sync-dot.err {
  background: var(--red);
  box-shadow: 0 0 0 3px rgba(204, 61, 61, 0.13);
}

.sync-msg {
  flex: 1;
  min-width: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-3);
}

.sync-msg.err {
  color: var(--red);
}

.sync-actions {
  display: flex;
  gap: 6px;
  flex: none;
}

/* 列表 */
.list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  padding: 12px;
  background: #f7f8fc;
}

.tools {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-block {
  padding: 12px;
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  background: #fff;
}

.tool-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 9px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-3);
}

.tool-label .icon {
  color: var(--brand);
}

.tool-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.tool-row .input {
  flex: 1;
  min-width: 120px;
  height: 36px;
}

.file-pick {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1.4;
  min-width: 190px;
  height: 36px;
  padding: 0 12px;
  border: 1px dashed #c6d0e3;
  border-radius: 10px;
  background: #fbfcfe;
  color: var(--text-3);
  font-size: 12.5px;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s, color 0.18s;
}

.file-pick:hover {
  border-color: var(--brand);
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.file-pick input {
  display: none;
}

.file-pick span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notice {
  margin-top: 9px;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 12px;
}

.result-meta {
  padding: 2px 4px;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-3);
}

/* 骨架屏 */
.sk-card {
  display: flex;
  gap: 12px;
  padding: 13px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
}

.sk-avatar {
  width: 38px;
  height: 38px;
  flex: none;
  border-radius: 11px;
  background: #eef1f7;
}

.sk-lines {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 7px;
  padding-top: 3px;
}

.sk-line {
  height: 9px;
  border-radius: 5px;
  background: #eef1f7;
}

.sk-avatar,
.sk-line {
  background-image: linear-gradient(90deg, #eef1f7 24%, #f7f9fd 40%, #eef1f7 56%);
  background-size: 320% 100%;
  animation: shimmer 1.35s ease-in-out infinite;
}

@keyframes shimmer {
  from {
    background-position: 120% 0;
  }
  to {
    background-position: -40% 0;
  }
}

.retry-btn {
  margin-top: 10px;
}

.empty-ico.err {
  background: var(--red-soft);
  color: var(--red);
}

/* 推荐记录 */
.rec-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.15s;
}

.rec-row:hover {
  border-color: var(--brand-line);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.rec-row:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}

.rec-avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  font-size: 12.5px;
}

.rec-main {
  flex: 1;
  min-width: 0;
}

.rec-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.rec-top b {
  font-size: 13.5px;
  font-weight: 700;
}

.rec-score {
  flex: none;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
}

.rec-main p {
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--text-3);
}

.rec-go {
  flex: none;
  color: #c2c9d8;
}

.rec-row:hover .rec-go {
  color: var(--brand);
}

@media (max-width: 1180px) {
  .workbench {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .workbench > :first-child {
    min-height: 420px;
  }

  .results {
    min-height: 520px;
    flex: none;
  }

  .list {
    min-height: 320px;
  }
}

@media (max-width: 760px) {
  .head-stats {
    display: none;
  }

  .results-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .seg {
    width: 100%;
  }

  .seg button {
    flex: 1;
  }

  .sync-bar {
    flex-wrap: wrap;
  }

  .sync-msg {
    flex-basis: 100%;
  }
}
</style>
