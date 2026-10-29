<template>
  <div class="login">
    <div class="bg-grid"></div>
    <div class="bg-glow glow-a"></div>
    <div class="bg-glow glow-b"></div>

    <div class="login-card">
      <!-- 品牌信息 -->
      <section class="brand-panel">
        <div class="brand-top">
          <span class="brand-mark"><AppIcon name="spark" :size="19" /></span>
          <span class="brand-name">AI 简历筛选助手</span>
        </div>

        <h1>
          让每一次筛选<br />
          都更接近<br />
          <em>对的人</em>
        </h1>
        <p class="slogan">BGE-M3 语义检索 · LangGraph Agent · 流式对话</p>

        <ul class="features">
          <li>
            <span class="num">01</span>
            <div>
              <b>语义级匹配</b>
              <em>理解用人需求，而不只是关键词堆砌</em>
            </div>
          </li>
          <li>
            <span class="num">02</span>
            <div>
              <b>对话式筛选</b>
              <em>一句「找 3 个会 Python 的前端」即可完成</em>
            </div>
          </li>
          <li>
            <span class="num">03</span>
            <div>
              <b>简历自动入库</b>
              <em>邮箱转发 PDF / Word，解析后立即参与检索</em>
            </div>
          </li>
        </ul>

        <div class="brand-foot">
          <span class="live-dot"></span>
          本地部署 · 简历数据不出内网
        </div>
      </section>

      <!-- 登录表单 -->
      <section class="form-panel">
        <p class="kicker">SIGN IN</p>
        <h2>欢迎回来</h2>
        <p class="sub">使用招聘账号进入你的 AI 工作台</p>

        <form class="form" @submit.prevent="onSubmit">
          <label class="field">
            <span class="field-label">账号</span>
            <div class="input-wrap">
              <AppIcon name="user" :size="17" />
              <input
                ref="accountEl"
                v-model="username"
                placeholder="请输入用户名"
                autocomplete="username"
                aria-label="账号"
                @input="error = ''"
              />
            </div>
          </label>

          <label class="field">
            <span class="field-label">密码</span>
            <div class="input-wrap">
              <AppIcon name="lock" :size="17" />
              <input
                ref="passwordEl"
                v-model="password"
                :type="showPwd ? 'text' : 'password'"
                placeholder="请输入密码"
                autocomplete="current-password"
                aria-label="密码"
                @input="error = ''"
              />
              <button
                type="button"
                class="eye"
                :aria-label="showPwd ? '隐藏密码' : '显示密码'"
                @click="showPwd = !showPwd"
              >
                <AppIcon :name="showPwd ? 'eyeOff' : 'eye'" :size="17" />
              </button>
            </div>
          </label>

          <p v-if="error" class="error" role="alert">
            <AppIcon name="alert" :size="15" />
            {{ error }}
          </p>

          <button type="submit" class="btn submit" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            {{ loading ? '正在验证…' : '进入工作台' }}
            <AppIcon v-if="!loading" name="arrowRight" :size="16" />
          </button>
        </form>

        <div class="demo">
          <span class="demo-label">演示账号</span>
          <button type="button" class="demo-chip" @click="fill('hr1', '123456')">
            hr1 / HR
          </button>
          <button type="button" class="demo-chip" @click="fill('tech1', '123456')">
            tech1 / 技术部
          </button>
          <button type="button" class="demo-chip" @click="fill('admin', '123456')">
            admin / 管理员
          </button>
          <button type="button" class="demo-chip" @click="fill('hukun', '12345678')">
            hukun / 管理员
          </button>
        </div>

        <p class="foot-hint">密码统一为 123456（hukun 为 12345678）· 登录即表示同意内部数据使用规范</p>
      </section>
    </div>

    <p class="copyright">© 2026 Resume Screener · 为招聘团队而做</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { homePath, setUser } from '../lib/auth.js'
import AppIcon from '../components/AppIcon.vue'

const router = useRouter()
const username = ref(localStorage.getItem('last_username') || '')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPwd = ref(false)
const accountEl = ref(null)
const passwordEl = ref(null)

onMounted(() => {
  if (username.value) passwordEl.value && passwordEl.value.focus()
  else accountEl.value && accountEl.value.focus()
})

function fill(u, p) {
  username.value = u
  password.value = p
  error.value = ''
}

async function onSubmit() {
  error.value = ''
  if (!username.value.trim()) {
    error.value = '请输入账号'
    accountEl.value && accountEl.value.focus()
    return
  }
  if (!password.value) {
    error.value = '请输入密码'
    passwordEl.value && passwordEl.value.focus()
    return
  }
  loading.value = true
  try {
    const data = await api.login(username.value.trim(), password.value)
    setUser(data)
    localStorage.setItem('last_username', data.username || username.value.trim())
    router.push(homePath())
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 40px 24px 68px;
  overflow: hidden;
  background: radial-gradient(1200px 700px at 12% -12%, #1b3a7e 0%, #0d1a33 46%, #080f1d 100%);
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 56px 56px;
  -webkit-mask-image: radial-gradient(circle at 50% 42%, #000 18%, transparent 76%);
  mask-image: radial-gradient(circle at 50% 42%, #000 18%, transparent 76%);
  pointer-events: none;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

.glow-a {
  top: -140px;
  left: -60px;
  width: 420px;
  height: 420px;
  background: rgba(70, 110, 255, 0.3);
}

.glow-b {
  right: -90px;
  bottom: -120px;
  width: 380px;
  height: 380px;
  background: rgba(124, 92, 255, 0.2);
}

.login-card {
  position: relative;
  display: grid;
  grid-template-columns: 1.04fr 0.96fr;
  width: 1000px;
  max-width: 100%;
  min-height: 574px;
  border-radius: 24px;
  overflow: hidden;
  background: var(--surface);
  box-shadow: var(--shadow-lg);
  animation: rise 0.5s ease both;
}

/* ---------- 左侧 ---------- */
.brand-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 46px 44px 40px;
  color: #fff;
  background: linear-gradient(158deg, #10254a 0%, #123a86 58%, #0c2a6b 100%);
  overflow: hidden;
}

.brand-panel::after {
  content: '';
  position: absolute;
  right: -120px;
  bottom: -150px;
  width: 340px;
  height: 340px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.09);
  box-shadow: 0 0 0 46px rgba(255, 255, 255, 0.03),
    0 0 0 92px rgba(255, 255, 255, 0.02);
  pointer-events: none;
}

.brand-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.13);
  border: 1px solid rgba(255, 255, 255, 0.16);
  color: #cdddff;
}

.brand-name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.9);
}

.brand-panel h1 {
  margin-top: 42px;
  font-size: 34px;
  font-weight: 700;
  line-height: 1.42;
  letter-spacing: -0.02em;
}

.brand-panel h1 em {
  font-style: normal;
  color: #9fbcff;
}

.slogan {
  margin-top: 14px;
  font-size: 12px;
  letter-spacing: 0.02em;
  color: rgba(255, 255, 255, 0.56);
}

.features {
  margin-top: 34px;
}

.features li {
  display: flex;
  gap: 14px;
  padding: 14px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.09);
}

.features .num {
  flex: none;
  padding-top: 1px;
  font-family: var(--mono);
  font-size: 11px;
  color: rgba(255, 255, 255, 0.36);
}

.features b {
  display: block;
  font-size: 13.5px;
  font-weight: 600;
}

.features em {
  display: block;
  margin-top: 3px;
  font-style: normal;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.55);
}

.brand-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 30px;
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.5);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4ade9f;
  box-shadow: 0 0 0 3px rgba(74, 222, 159, 0.18);
}

/* ---------- 右侧 ---------- */
.form-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 44px;
}

.kicker {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.19em;
  color: var(--brand);
}

.form-panel h2 {
  margin-top: 10px;
  font-size: 25px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.sub {
  margin-top: 6px;
  font-size: 13px;
  color: var(--text-3);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 28px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 46px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fafbfe;
  color: #9aa4b8;
  transition: border-color 0.18s, box-shadow 0.18s, background 0.18s, color 0.18s;
}

.input-wrap:focus-within {
  border-color: var(--brand);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(36, 86, 230, 0.1);
  color: var(--brand);
}

.input-wrap input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--text);
}

.input-wrap input::placeholder {
  color: #b0b9c9;
}

.eye {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  color: #9aa4b8;
  transition: color 0.18s;
}

.eye:hover {
  color: var(--text-2);
}

.error {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--red-soft);
  color: var(--red);
  font-size: 12.5px;
}

.submit {
  height: 46px;
  margin-top: 4px;
  border-radius: 12px;
  font-size: 14.5px;
  letter-spacing: 0.03em;
  background: linear-gradient(135deg, #2f63f0, #1a3fbd);
}

.submit:hover {
  background: linear-gradient(135deg, #2456e6, #16369f);
  box-shadow: 0 12px 26px -12px rgba(36, 86, 230, 0.9);
}

.spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

.demo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  margin-top: 26px;
  padding-top: 18px;
  border-top: 1px dashed var(--line);
}

.demo-label {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.13em;
  color: var(--text-3);
  margin-right: 2px;
}

.demo-chip {
  height: 26px;
  padding: 0 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: #f6f8fc;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-2);
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}

.demo-chip:hover {
  border-color: var(--brand-line);
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.foot-hint {
  margin-top: 22px;
  font-size: 11px;
  color: #a3acbd;
}

.copyright {
  position: absolute;
  bottom: 22px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.32);
}

/* ---------- 响应式 ---------- */
@media (max-width: 900px) {
  .login-card {
    grid-template-columns: 1fr;
    min-height: auto;
    width: 520px;
  }

  .brand-panel {
    padding: 30px 32px 26px;
  }

  .brand-panel h1 {
    margin-top: 24px;
    font-size: 26px;
    line-height: 1.4;
  }

  .features,
  .brand-foot {
    display: none;
  }

  .form-panel {
    padding: 32px;
  }
}

@media (max-width: 560px) {
  .login {
    padding: 20px 14px 56px;
  }

  .login-card {
    border-radius: 18px;
  }

  .brand-panel {
    padding: 24px 22px 20px;
  }

  .brand-panel h1 {
    margin-top: 18px;
    font-size: 22px;
  }

  .slogan {
    margin-top: 10px;
  }

  .form-panel {
    padding: 26px 22px 30px;
  }

  .form-panel h2 {
    font-size: 22px;
  }
}
</style>
