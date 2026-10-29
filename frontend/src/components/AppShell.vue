<template>
  <div class="shell">
    <a class="skip-link" href="#main-body">跳到主要内容</a>

    <aside class="rail">
      <router-link to="/" class="rail-brand" aria-label="AI 简历筛选助手首页">
        <span class="rail-mark"><AppIcon name="spark" :size="17" /></span>
        <span class="rail-wordmark">
          <b>招聘助手</b>
          <em>RESUME SCREENER</em>
        </span>
      </router-link>

      <nav class="rail-nav" aria-label="主导航">
        <router-link
          v-if="canScreen"
          to="/"
          class="nav-item"
          :class="{ active: onWorkbench }"
          :aria-current="onWorkbench ? 'page' : undefined"
        >
          <AppIcon name="workspace" :size="18" />
          <span>工作台</span>
        </router-link>
        <router-link
          to="/kanban"
          class="nav-item"
          :class="{ active: onKanban }"
          :aria-current="onKanban ? 'page' : undefined"
        >
          <AppIcon name="board" :size="18" />
          <span>候选人看板</span>
        </router-link>
        <router-link
          to="/interviews"
          class="nav-item"
          :class="{ active: onInterviews }"
          :aria-current="onInterviews ? 'page' : undefined"
        >
          <AppIcon name="clock" :size="18" />
          <span>面试管理</span>
        </router-link>
        <router-link
          v-if="isAdmin"
          to="/users"
          class="nav-item"
          :class="{ active: onUsers }"
          :aria-current="onUsers ? 'page' : undefined"
        >
          <AppIcon name="lock" :size="18" />
          <span>账号与权限</span>
        </router-link>
      </nav>

      <div class="rail-foot">
        <div class="rail-user">
          <span class="rail-avatar">{{ initials }}</span>
          <span class="rail-user-text">
            <b>{{ displayName }}</b>
            <em>{{ roleLabel }}</em>
          </span>
          <button class="rail-logout" type="button" aria-label="退出登录" title="退出登录" @click="logout">
            <AppIcon name="logout" :size="16" />
          </button>
        </div>
        <p class="rail-note">LangGraph · FAISS</p>
      </div>
    </aside>

    <div id="main-body" class="main" tabindex="-1">
      <header class="page-head">
        <div class="head-text">
          <p class="kicker"><span class="kicker-dot"></span>{{ kicker }}</p>
          <h1>{{ title }}</h1>
          <p v-if="subtitle" class="head-sub">{{ subtitle }}</p>
        </div>
        <div class="head-actions">
          <slot name="actions" />
        </div>
      </header>
      <div class="page-body">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'
import { canScreen, clearUser, isAdmin, roleLabel, user } from '../lib/auth.js'
import AppIcon from './AppIcon.vue'

defineProps({
  kicker: { type: String, default: '' },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const route = useRoute()
const router = useRouter()

const displayName = computed(() => user.value.display_name || user.value.username || '未登录')
const initials = computed(() => (user.value.username || '?').slice(0, 1).toUpperCase())

const onWorkbench = computed(
  () => route.path === '/' || route.path.startsWith('/candidates'),
)
const onKanban = computed(() => route.path.startsWith('/kanban'))
const onInterviews = computed(() => route.path.startsWith('/interviews'))
const onUsers = computed(() => route.path.startsWith('/users'))

async function logout() {
  try {
    await api.logout()
  } catch {
    // 后端会话已失效也照常退出
  }
  clearUser()
  router.push('/login')
}
</script>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.skip-link {
  position: absolute;
  top: 10px;
  left: -9999px;
  z-index: 200;
  padding: 8px 14px;
  border-radius: 9px;
  background: #fff;
  color: var(--brand-strong);
  font-size: 12.5px;
  font-weight: 600;
  box-shadow: var(--shadow);
}

.skip-link:focus {
  left: 12px;
}

.main:focus {
  outline: none;
}

/* ---------- 左侧导航 ---------- */
.rail {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 228px;
  flex: none;
  padding: 22px 14px 16px;
  color: #fff;
  background: linear-gradient(180deg, #0d1729 0%, #101c33 55%, #0a1322 100%);
  overflow: hidden;
}

.rail::after {
  content: '';
  position: absolute;
  top: -110px;
  right: -100px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(64, 110, 255, 0.38), transparent 68%);
  pointer-events: none;
}

.rail-brand {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 8px;
}

.rail-mark {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 10px;
  background: linear-gradient(145deg, #3a6bff, #1a3fbd);
  box-shadow: 0 8px 18px -8px rgba(58, 107, 255, 0.9);
  color: #fff;
}

.rail-wordmark {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.rail-wordmark b {
  font-size: 14.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.rail-wordmark em {
  font-style: normal;
  font-size: 8.5px;
  font-weight: 500;
  letter-spacing: 0.19em;
  color: rgba(255, 255, 255, 0.38);
}

.rail-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 30px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 11px;
  height: 40px;
  padding: 0 12px;
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.18s, color 0.18s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(70, 110, 240, 0.34), rgba(70, 110, 240, 0.08));
  color: #fff;
  font-weight: 600;
}

.nav-item.active .icon {
  color: #9db6ff;
}

.rail-foot {
  margin-top: auto;
  position: relative;
}

.rail-user {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
}

.rail-avatar {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: 9px;
  background: linear-gradient(145deg, #4d7bff, #2456e6);
  font-size: 12px;
  font-weight: 700;
}

.rail-user-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.rail-user-text b {
  font-size: 12.5px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rail-user-text em {
  font-style: normal;
  font-size: 10.5px;
  color: rgba(255, 255, 255, 0.4);
}

.rail-logout {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.45);
  transition: background 0.18s, color 0.18s;
}

.rail-logout:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.rail-note {
  margin-top: 12px;
  text-align: center;
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.24);
}

/* ---------- 主区域 ---------- */
.main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  background: var(--paper);
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  padding: 26px 30px 18px;
}

.kicker {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.17em;
  text-transform: uppercase;
  color: var(--text-3);
}

.kicker-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 3px rgba(36, 86, 230, 0.14);
}

.head-text h1 {
  margin-top: 7px;
  font-size: 25px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.head-sub {
  margin-top: 5px;
  font-size: 13px;
  color: var(--text-3);
}

.head-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.page-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 30px 26px;
  overflow: hidden;
}

/* ---------- 响应式 ---------- */
@media (max-width: 1100px) {
  .rail {
    width: 76px;
    padding: 18px 10px 14px;
  }

  .rail-brand {
    justify-content: center;
    padding: 0;
  }

  .rail-wordmark,
  .rail-user-text,
  .rail-note {
    display: none;
  }

  .nav-item {
    justify-content: center;
    padding: 0;
  }

  .nav-item span {
    display: none;
  }

  .rail-user {
    flex-direction: column;
    gap: 6px;
    padding: 8px 4px;
  }
}

@media (max-width: 760px) {
  .shell {
    flex-direction: column;
  }

  .rail {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 40;
    width: auto;
    height: 62px;
    flex-direction: row;
    align-items: center;
    padding: 0 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .rail::after,
  .rail-brand,
  .rail-foot {
    display: none;
  }

  .rail-nav {
    flex: 1;
    flex-direction: row;
    justify-content: space-around;
    gap: 6px;
    margin-top: 0;
  }

  .nav-item {
    flex-direction: column;
    gap: 2px;
    height: 50px;
    padding: 0 16px;
    font-size: 10.5px;
    border-radius: 10px;
  }

  .nav-item span {
    display: inline;
  }

  .main {
    padding-bottom: 62px;
  }

  .page-head {
    padding: 20px 18px 14px;
  }

  .head-text h1 {
    font-size: 21px;
  }

  .page-body {
    padding: 0 18px 18px;
  }
}
</style>
