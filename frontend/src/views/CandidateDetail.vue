<template>
  <div class="app-shell">
    <header class="topbar">
      <span class="brand back" @click="$router.push('/')">← 返回工作台</span>
      <span class="brand">简历详情</span>
      <div class="actions">
        <template v-if="!editing">
          <button class="btn btn-ghost" @click="startEdit">编辑</button>
          <button class="btn btn-danger" @click="remove">删除</button>
        </template>
        <template v-else>
          <button class="btn btn-ghost" @click="cancelEdit">取消</button>
          <button class="btn" @click="save">保存</button>
        </template>
      </div>
    </header>

    <div class="content">
      <!-- 编辑模式：表单 -->
      <div class="card detail" v-if="c && editing">
        <h2 class="form-title">编辑候选人信息</h2>
        <div class="edit-form">
          <label>姓名<input v-model="form.name" class="f-input" /></label>
          <label>意向岗位<input v-model="form.expected_position" class="f-input" /></label>
          <label>技能<input v-model="form.skills" class="f-input" /></label>
          <label>经历<input v-model="form.experience" class="f-input" /></label>
          <label>学历<input v-model="form.education" class="f-input" /></label>
          <label>电话<input v-model="form.phone" class="f-input" /></label>
          <label>邮箱<input v-model="form.email" class="f-input" /></label>
        </div>
      </div>

      <!-- 只读模式：详情展示 -->
      <div class="card detail" v-else-if="c">
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
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'

const route = useRoute()
const router = useRouter()
const c = ref(null)
const editing = ref(false)
const form = ref({})

async function load() {
  const data = await api.candidate(route.params.id)
  c.value = data.candidate
}

function startEdit() {
  form.value = {
    name: c.value.name || '',
    expected_position: c.value.expected_position || '',
    skills: c.value.skills || '',
    experience: c.value.experience || '',
    education: c.value.education || '',
    phone: c.value.phone || '',
    email: c.value.email || '',
  }
  editing.value = true
}

function cancelEdit() {
  editing.value = false
}

async function save() {
  const data = await api.updateCandidate(c.value.id, form.value)
  c.value = data.candidate
  editing.value = false
}

async function remove() {
  if (!window.confirm('确定删除该候选人吗？删除后不可恢复')) return
  await api.deleteCandidate(c.value.id)
  router.push('/')
}

onMounted(load)
</script>

<style scoped>
.back {
  cursor: pointer;
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-danger {
  background: #e74c3c;
  color: #fff;
}

.btn-danger:hover {
  background: #c0392b;
}

.detail {
  flex: 1;
  padding: 28px 32px;
  overflow-y: auto;
}

.form-title {
  font-size: 18px;
  margin: 0 0 20px;
}

.edit-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 720px;
}

.edit-form label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #555;
}

.f-input {
  padding: 9px 12px;
  border: 1px solid #e5e8f0;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.f-input:focus {
  border-color: #1a6fe0;
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