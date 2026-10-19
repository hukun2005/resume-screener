<template>
  <div class="app-shell">
    <header class="topbar">
      <span class="brand">AI 简历筛选助手</span>
      <div class="user">
        <span>{{ username }}</span>
        <button class="btn btn-ghost" @click="logout">退出登录</button>
      </div>
    </header>

    <div class="content">
      <AgentChat @result="onResult" />

      <div class="panel right">
        <div class="tabs">
          <button :class="{ active: tab === 'recommend' }" @click="tab = 'recommend'">AI 推荐</button>
          <button :class="{ active: tab === 'all' }" @click="tab = 'all'">简历库</button>
          <button :class="{ active: tab === 'sent' }" @click="tab = 'sent'">已推荐</button>
        </div>

        <div class="list">
          <template v-if="tab === 'recommend'">
            <p v-if="!recommendList.length" class="empty">
              在左侧输入需求（如「找 3 个会 Python 的前端」），AI 会推荐匹配简历
            </p>
            <CandidateCard
              v-for="c in recommendList"
              :key="c.id"
              :c="c"
              @click="goDetail(c.id)"
            />
          </template>

          <template v-else-if="tab === 'all'">
            <div class="upload-box">
              <input v-model="upName" class="up-input" placeholder="候选人姓名" />
              <input v-model="upPosition" class="up-input" placeholder="意向岗位（可选）" />
              <input type="file" accept=".pdf,.docx,.doc,.txt" class="up-file" @change="onFile" />
              <button class="btn" @click="doUpload" :disabled="uploading">
                {{ uploading ? '解析中…' : '上传解析' }}
              </button>
            </div>
            <p v-if="upMsg" class="up-msg">{{ upMsg }}</p>
            <CandidateCard
              v-for="c in allCandidates"
              :key="c.id"
              :c="c"
              @click="goDetail(c.id)"
            />
          </template>

          <template v-else>
            <div v-for="r in recommendations" :key="r.id" class="rec-row">
              <span class="r-name">{{ r.candidate_name }}</span>
              <span class="r-req">{{ r.requirement }}</span>
              <span class="r-score">{{ r.match_score }}%</span>
            </div>
            <p v-if="!recommendations.length" class="empty">暂无推荐记录</p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import AgentChat from '../components/AgentChat.vue'
import CandidateCard from '../components/CandidateCard.vue'

const router = useRouter()
const username = localStorage.getItem('username') || 'admin'
const tab = ref('recommend')
const recommendList = ref([])
const allCandidates = ref([])
const recommendations = ref([])

const upName = ref('')
const upPosition = ref('')
const upFile = ref(null)
const uploading = ref(false)
const upMsg = ref('')

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
    await loadAll()
  } catch (e) {
    upMsg.value = '上传失败：' + e.message
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
  const data = await api.candidates()
  allCandidates.value = data.candidates
}

async function loadRecommendations() {
  const data = await api.recommendations()
  recommendations.value = data.recommendations
}

function goDetail(id) {
  router.push('/candidates/' + id)
}

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('username')
  router.push('/login')
}

onMounted(() => {
  loadAll()
  loadRecommendations()
})
</script>

<style scoped>
.right {
  flex: 1;
}

.list {
  flex: 1;
  overflow-y: auto;
}

.empty {
  color: #999;
  font-size: 14px;
  text-align: center;
  padding: 40px 16px;
}

.rec-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f1f6;
  font-size: 14px;
}

.r-name {
  font-weight: 600;
}

.r-req {
  flex: 1;
  color: #666;
  font-size: 13px;
}

.r-score {
  color: #1a6fe0;
  font-weight: 700;
}

.upload-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f1f6;
  align-items: center;
}

.up-input {
  flex: 1;
  min-width: 120px;
  padding: 8px 10px;
  border: 1px solid #e5e8f0;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
}

.up-file {
  font-size: 13px;
}

.up-msg {
  margin: 0;
  padding: 8px 16px;
  font-size: 13px;
  color: #1a6fe0;
}
</style>