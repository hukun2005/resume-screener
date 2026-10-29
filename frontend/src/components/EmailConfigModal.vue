<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div
      ref="panel"
      class="modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="email-title"
      tabindex="-1"
      @keydown="onKeydown"
    >
      <header class="modal-head">
        <span class="modal-ico"><AppIcon name="mail" :size="20" /></span>
        <div class="modal-head-text">
          <h3 id="email-title">绑定简历邮箱</h3>
          <p>招聘平台「简历转发到邮箱」发来的 PDF / Word 附件，会自动解析并入库。</p>
        </div>
        <button class="modal-close" type="button" aria-label="关闭" @click="$emit('close')">
          <AppIcon name="close" :size="18" />
        </button>
      </header>

      <div class="modal-body scroll">
        <div class="grid">
          <label class="field">
            <span>邮箱账号</span>
            <input
              ref="userEl"
              v-model.trim="form.user"
              class="input"
              placeholder="hr@qq.com"
              @change="autoHost"
            />
          </label>

          <label class="field">
            <span>IMAP 服务器</span>
            <input v-model.trim="form.host" class="input" placeholder="imap.qq.com" />
          </label>

          <label class="field">
            <span>端口</span>
            <input v-model.number="form.port" type="number" class="input" placeholder="993" />
          </label>

          <label class="field">
            <span>授权码 / 密码</span>
            <input
              ref="pwEl"
              v-model="form.password"
              type="password"
              class="input"
              :placeholder="hasPassword ? '已保存，留空则不修改' : 'IMAP 授权码（非登录密码）'"
            />
          </label>

          <label class="field">
            <span>收件箱</span>
            <input v-model.trim="form.mailbox" class="input" placeholder="INBOX" />
          </label>

          <label class="field">
            <span>回溯天数</span>
            <input v-model.number="form.search_days" type="number" class="input" />
          </label>

          <label class="field wide">
            <span>自动同步间隔（秒）</span>
            <input v-model.number="form.poll_interval" type="number" class="input" />
          </label>
        </div>

        <label class="switch-row">
          <input v-model="form.use_ssl" type="checkbox" />
          <span class="switch"><i></i></span>
          <span class="switch-text">
            <b>使用 SSL 加密连接</b>
            <em>993 端口的 IMAP 服务通常需要开启</em>
          </span>
        </label>

        <p v-if="msg" class="msg" :class="{ err: isError }" role="status" aria-live="polite">
          <AppIcon :name="isError ? 'alert' : 'check'" :size="14" />
          {{ msg }}
        </p>
      </div>

      <footer class="modal-foot">
        <button class="btn btn-ghost" :disabled="busy" @click="test">
          <AppIcon name="sync" :size="15" />测试连接
        </button>
        <span class="foot-spacer"></span>
        <button class="btn btn-ghost" :disabled="busy" @click="$emit('close')">取消</button>
        <button class="btn" :disabled="busy" @click="save">
          {{ busy ? '处理中…' : '保存并启用' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { api } from '../api.js'
import AppIcon from './AppIcon.vue'

const emit = defineEmits(['close', 'saved'])

const panel = ref(null)
const userEl = ref(null)
const pwEl = ref(null)

const form = reactive({
  host: '',
  port: 993,
  user: '',
  password: '',
  mailbox: 'INBOX',
  use_ssl: true,
  search_days: 7,
  max_per_run: 50,
  poll_interval: 300,
})

const hasPassword = ref(false)
const busy = ref(false)
const msg = ref('')
const isError = ref(false)

// 常见邮箱服务商填好账号后自动补全服务器
const HOSTS = {
  'qq.com': 'imap.qq.com',
  'foxmail.com': 'imap.qq.com',
  '163.com': 'imap.163.com',
  '126.com': 'imap.126.com',
  'yeah.net': 'imap.yeah.net',
  'gmail.com': 'imap.gmail.com',
  'outlook.com': 'outlook.office365.com',
  'hotmail.com': 'outlook.office365.com',
  'aliyun.com': 'imap.aliyun.com',
}

function autoHost() {
  if (form.host) return
  const domain = (form.user.split('@')[1] || '').toLowerCase()
  if (HOSTS[domain]) form.host = HOSTS[domain]
}

function payload() {
  return { ...form }
}

function show(text, error = false) {
  msg.value = text
  isError.value = error
}

async function test() {
  if (!requireFields()) return
  busy.value = true
  show('正在连接邮箱…')
  try {
    const r = await api.testEmailConfig(payload())
    show(`连接成功：收件箱 ${r.mailbox}，近 ${form.search_days} 天有 ${r.recent_messages} 封邮件`)
  } catch (e) {
    show(e.message, true)
  } finally {
    busy.value = false
  }
}

async function save() {
  if (!requireFields()) return
  busy.value = true
  show('正在保存…')
  try {
    await api.saveEmailConfig(payload())
    emit('saved')
  } catch (e) {
    show(e.message, true)
  } finally {
    busy.value = false
  }
}

function requireFields() {
  if (!form.user) {
    show('请填写邮箱账号', true)
    userEl.value && userEl.value.focus()
    return false
  }
  if (!form.host) {
    show('请填写 IMAP 服务器地址', true)
    return false
  }
  if (!form.password && !hasPassword.value) {
    show('请填写 IMAP 授权码', true)
    pwEl.value && pwEl.value.focus()
    return false
  }
  return true
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])'

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
    return
  }
  if (e.key !== 'Tab' || !panel.value) return
  const items = Array.from(panel.value.querySelectorAll(FOCUSABLE)).filter(
    (el) => el.offsetParent !== null
  )
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(async () => {
  document.body.style.overflow = 'hidden'
  nextTick(() => panel.value && panel.value.focus())
  try {
    const c = await api.emailConfig()
    form.host = c.host || ''
    form.port = c.port || 993
    form.user = c.user || ''
    form.mailbox = c.mailbox || 'INBOX'
    form.use_ssl = !!c.use_ssl
    form.search_days = c.search_days || 7
    form.max_per_run = c.max_per_run || 50
    form.poll_interval = c.poll_interval ?? 300
    hasPassword.value = !!c.has_password
  } catch (e) {
    show('读取现有配置失败：' + e.message, true)
  }
})

onBeforeUnmount(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(9, 17, 32, 0.5);
  backdrop-filter: blur(5px);
  animation: fade-in 0.18s ease both;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal {
  display: flex;
  flex-direction: column;
  width: 660px;
  max-width: 100%;
  max-height: 88vh;
  border-radius: var(--radius-xl);
  background: #fff;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: rise 0.24s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.modal-head {
  display: flex;
  align-items: flex-start;
  gap: 13px;
  padding: 22px 24px 18px;
  border-bottom: 1px solid var(--line-soft);
}

.modal-ico {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex: none;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.modal-head-text {
  flex: 1;
  min-width: 0;
}

.modal-head-text h3 {
  font-size: 16.5px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.modal-head-text p {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-3);
}

.modal-close {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: none;
  margin: -4px -6px 0 0;
  border-radius: 8px;
  color: var(--text-3);
  transition: background 0.18s, color 0.18s;
}

.modal-close:hover {
  background: #f1f4f9;
  color: var(--text);
}

.modal-body {
  flex: 1;
  min-height: 0;
  padding: 22px 24px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field.wide {
  grid-column: 1 / -1;
}

.field > span {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.switch-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fbfcfe;
  cursor: pointer;
}

.switch-row input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
}

.switch {
  position: relative;
  width: 38px;
  height: 22px;
  flex: none;
  border-radius: 999px;
  background: #d5dbe7;
  transition: background 0.2s;
}

.switch i {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 26, 48, 0.25);
  transition: transform 0.2s;
}

.switch-row input:checked + .switch {
  background: var(--brand);
}

.switch-row input:checked + .switch i {
  transform: translateX(16px);
}

.switch-row input:focus-visible + .switch {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}

.switch-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.switch-text b {
  font-size: 13px;
  font-weight: 600;
}

.switch-text em {
  font-style: normal;
  font-size: 11.5px;
  color: var(--text-3);
}

.msg {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding: 9px 11px;
  border-radius: 9px;
  background: var(--green-soft);
  color: var(--green);
  font-size: 12.5px;
  line-height: 1.5;
}

.msg.err {
  background: var(--red-soft);
  color: var(--red);
}

.msg .icon {
  flex: none;
}

.modal-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid var(--line-soft);
  background: #fafbfe;
}

.foot-spacer {
  flex: 1;
}

@media (max-width: 620px) {
  .modal-mask {
    padding: 12px;
    align-items: flex-end;
  }

  .modal {
    max-height: 92vh;
    border-radius: 18px;
  }

  .modal-head,
  .modal-body,
  .modal-foot {
    padding-left: 18px;
    padding-right: 18px;
  }

  .grid {
    grid-template-columns: 1fr;
  }

  .modal-foot {
    flex-wrap: wrap;
  }
}
</style>
