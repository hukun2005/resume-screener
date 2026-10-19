<template>
  <div class="app-shell">
    <header class="topbar">
      <span class="brand back" @click="$router.push('/')">← 返回工作台</span>
      <span class="brand">简历详情</span>
    </header>

    <div class="content">
      <div class="card detail" v-if="c">
        <div class="head">
          <h1>{{ c.name }}</h1>
          <span class="pos">{{ c.expected_position }}</span>
        </div>
        <div class="grid">
          <div class="row"><b>技能：</b>{{ c.skills }}</div>
          <div class="row"><b>经历：</b>{{ c.experience }}</div>
          <div class="row"><b>学历：</b>{{ c.education }}</div>
          <div class="row"><b>电话：</b>{{ c.phone }}</div>
          <div class="row"><b>邮箱：</b>{{ c.email }}</div>
        </div>
        <div class="intro">
          <b>简历简介</b>
          <p>{{ c.resume_text }}</p>
        </div>
      </div>
      <p v-else class="empty">加载中…</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api.js'

const route = useRoute()
const c = ref(null)

onMounted(async () => {
  const data = await api.candidate(route.params.id)
  c.value = data.candidate
})
</script>

<style scoped>
.back {
  cursor: pointer;
}

.detail {
  flex: 1;
  padding: 28px 32px;
  overflow-y: auto;
}

.head {
  border-bottom: 2px solid #eef4ff;
  padding-bottom: 16px;
  margin-bottom: 20px;
}

.head h1 {
  font-size: 26px;
}

.pos {
  display: inline-block;
  margin-top: 8px;
  color: #1a6fe0;
  font-size: 14px;
  background: #eef4ff;
  padding: 4px 12px;
  border-radius: 20px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 24px;
}

.row {
  font-size: 14px;
  color: #333;
}

.intro b {
  display: block;
  margin-bottom: 8px;
  font-size: 15px;
}

.intro p {
  color: #555;
  font-size: 14px;
  line-height: 1.8;
}

.empty {
  color: #999;
  padding: 40px;
}
</style>