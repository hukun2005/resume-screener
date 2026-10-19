<template>
  <div class="login-wrap">
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>

    <div class="login-card">
      <!-- 左侧品牌区 -->
      <div class="brand-panel">
        <div class="logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
            <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4h13A1.5 1.5 0 0 1 20 5.5v9a1.5 1.5 0 0 1-1.5 1.5h-11L4 19.5V5.5Z" stroke-linejoin="round" />
            <path d="M8.5 8.5h7M8.5 11.5h7" stroke-linecap="round" />
          </svg>
        </div>
        <h1>AI 简历筛选助手</h1>
        <p class="slogan">基于大模型的智能招聘推荐系统</p>

        <ul class="features">
          <li>
            <span class="dot"></span>
            <div><b>智能语义匹配</b><em>向量化检索，理解招聘需求</em></div>
          </li>
          <li>
            <span class="dot"></span>
            <div><b>流式对话体验</b><em>AI 逐字输出，即时响应</em></div>
          </li>
          <li>
            <span class="dot"></span>
            <div><b>简历自动解析</b><em>上传 PDF / Word 一键入库</em></div>
          </li>
        </ul>
      </div>

      <!-- 右侧表单区 -->
      <div class="form-panel">
        <h2>欢迎登录</h2>
        <p class="sub2">请使用账号密码进入工作台</p>

        <form @submit.prevent="onSubmit">
          <div class="input-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <circle cx="12" cy="8" r="3.5" />
              <path d="M5 20c.8-3.3 3.6-5 7-5s6.2 1.7 7 5" stroke-linecap="round" />
            </svg>
            <input v-model="username" placeholder="用户名" autocomplete="username" />
          </div>

          <div class="input-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <rect x="5" y="10.5" width="14" height="9" rx="2" />
              <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" />
            </svg>
            <input
              v-model="password"
              :type="showPwd ? 'text' : 'password'"
              placeholder="密码"
              autocomplete="current-password"
            />
            <button type="button" class="eye" @click="showPwd = !showPwd" tabindex="-1">
              <svg v-if="!showPwd" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
                <circle cx="12" cy="12" r="2.8" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
                <circle cx="12" cy="12" r="2.8" />
                <path d="M3 3l18 18" stroke-linecap="round" />
              </svg>
            </button>
          </div>

          <p v-if="error" class="error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7.5v5.5M12 16.5h.01" stroke-linecap="round" />
            </svg>
            {{ error }}
          </p>

          <button type="submit" class="login-btn" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '登录中…' : '登 录' }}
          </button>
        </form>

        <p class="hint">演示账号：admin / 123456 ｜ hukun / 12345678</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPwd = ref(false)

async function onSubmit() {
  error.value = ''
  loading.value = true
  try {
    const data = await api.login(username.value, password.value)
    localStorage.setItem('token', data.token)
    localStorage.setItem('username', data.username)
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: radial-gradient(1200px 600px at 80% -10%, #2a5cc8 0%, #123b8f 45%, #0a1f4d 100%);
  overflow: hidden;
}

.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.4;
  pointer-events: none;
}

.glow-1 {
  width: 360px;
  height: 360px;
  background: #4f8ef7;
  top: -120px;
  left: -80px;
}

.glow-2 {
  width: 300px;
  height: 300px;
  background: #7fb0ff;
  bottom: -100px;
  right: -60px;
  opacity: 0.25;
}

.login-card {
  position: relative;
  width: 860px;
  max-width: 100%;
  min-height: 520px;
  display: flex;
  border-radius: 20px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 30px 80px rgba(5, 20, 55, 0.45);
  animation: rise 0.5s ease;
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(18px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 左侧品牌区 */
.brand-panel {
  flex: 1.1;
  padding: 48px 44px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(160deg, #1a6fe0 0%, #1558b0 60%, #123b8f 100%);
  color: #fff;
}

.logo {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.16);
  margin-bottom: 22px;
}

.logo svg {
  width: 26px;
  height: 26px;
}

.brand-panel h1 {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.3;
}

.slogan {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.72);
  margin: 10px 0 40px;
}

.features {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.features li {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.features .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #7fb0ff;
  margin-top: 6px;
  box-shadow: 0 0 0 4px rgba(127, 176, 255, 0.22);
}

.features b {
  display: block;
  font-size: 15px;
  font-weight: 600;
}

.features em {
  font-style: normal;
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.65);
  margin-top: 2px;
  display: block;
}

/* 右侧表单区 */
.form-panel {
  flex: 1;
  padding: 48px 44px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.form-panel h2 {
  font-size: 26px;
  color: #1f2d4d;
}

.sub2 {
  color: #8a94a6;
  font-size: 14px;
  margin: 8px 0 30px;
}

.input-box {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1.5px solid #e3e8f2;
  border-radius: 10px;
  padding: 0 14px;
  margin-bottom: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fbfcfe;
}

.input-box:focus-within {
  border-color: #1a6fe0;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(26, 111, 224, 0.1);
}

.input-box > svg {
  width: 18px;
  height: 18px;
  color: #9aa6bd;
  flex-shrink: 0;
}

.input-box:focus-within > svg {
  color: #1a6fe0;
}

.input-box input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  padding: 13px 0;
  font-size: 15px;
  color: #1f2d4d;
}

.input-box input::placeholder {
  color: #b6bfcf;
}

.eye {
  border: none;
  background: transparent;
  color: #9aa6bd;
  width: 22px;
  height: 22px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.eye svg {
  width: 20px;
  height: 20px;
}

.error {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #e5484d;
  font-size: 13px;
  margin: -4px 0 14px;
}

.error svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.login-btn {
  width: 100%;
  border: none;
  border-radius: 10px;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  background: linear-gradient(135deg, #1a6fe0, #1558b0);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: transform 0.15s, box-shadow 0.2s;
}

.login-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(26, 111, 224, 0.35);
}

.login-btn:disabled {
  opacity: 0.75;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.hint {
  text-align: center;
  color: #a7b0bf;
  font-size: 12.5px;
  margin-top: 26px;
}

@media (max-width: 640px) {
  .brand-panel {
    display: none;
  }
  .form-panel {
    padding: 40px 28px;
  }
  .login-card {
    min-height: auto;
  }
}
</style>