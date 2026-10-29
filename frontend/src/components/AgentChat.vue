<template>
  <section class="panel agent">
    <header class="panel-head chat-head">
      <div class="chat-title">
        <span class="ai-mark"><AppIcon name="spark" :size="16" /></span>
        <div>
          <h2 class="panel-title">AI 筛选助手</h2>
          <p class="panel-sub">语义检索 · 工具调用 · 流式输出</p>
        </div>
      </div>
      <div class="chat-tools">
        <span class="live"><i></i>在线</span>
        <button
          v-if="messages.length"
          class="btn btn-ghost btn-sm"
          type="button"
          :disabled="loading"
          @click="clearChat"
        >
          <AppIcon name="trash" :size="14" />
          清空
        </button>
      </div>
    </header>

    <div ref="box" class="msgs scroll" role="log" aria-live="polite" aria-label="对话记录">
      <div v-if="!messages.length" class="chat-empty">
        <div class="chat-empty-mark"><AppIcon name="spark" :size="26" /></div>
        <h4>把需求说给 AI 听</h4>
        <p>它会先在简历库做语义检索，再把匹配的候选人推荐给你。</p>
        <div class="suggests">
          <button v-for="s in suggestions" :key="s" type="button" class="suggest" @click="send(s)">
            <span>{{ s }}</span>
            <AppIcon name="arrowRight" :size="14" />
          </button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" :class="['msg-row', m.role]">
        <span v-if="m.role === 'assistant'" class="msg-avatar ai">
          <AppIcon name="spark" :size="13" />
        </span>
        <div class="msg-body">
          <div
            class="bubble"
            :class="{ typing: m.role === 'assistant' && !m.content && loading, failed: m.failed }"
          >
            <span v-if="m.role === 'assistant' && !m.content && loading" class="dots">
              <i></i><i></i><i></i>
            </span>
            <template v-else>{{ m.content }}</template>
          </div>
          <button
            v-if="m.failed && !loading"
            type="button"
            class="retry"
            @click="retry(i)"
          >
            <AppIcon name="refresh" :size="13" />
            重新生成
          </button>
        </div>
        <span v-if="m.role === 'user'" class="msg-avatar me">{{ userInitial }}</span>
      </div>
    </div>

    <div class="composer">
      <div class="composer-box">
        <input
          v-model="input"
          :disabled="loading"
          placeholder="描述你的用人需求，例如：找 3 个会 Python 的前端"
          @keyup.enter="send()"
        />
        <button
          v-if="loading"
          class="send-btn stop"
          type="button"
          aria-label="停止生成"
          @click="stop"
        >
          <AppIcon name="stop" :size="16" />
        </button>
        <button
          v-else
          class="send-btn"
          type="button"
          aria-label="发送"
          :disabled="!input.trim()"
          @click="send()"
        >
          <AppIcon name="send" :size="17" />
        </button>
      </div>
      <p class="composer-hint">
        {{ loading ? '正在生成，可点击右侧按钮停止' : 'Enter 发送 · Esc 停止生成 · AI 内容仅供参考' }}
      </p>
    </div>
  </section>
</template>

<script setup>
import { ref, nextTick, onBeforeUnmount } from 'vue'
import { chatStream, api } from '../api.js'
import { toast, confirmAction } from '../lib/ui.js'
import AppIcon from './AppIcon.vue'

const emit = defineEmits(['result'])
const messages = ref([])
const input = ref('')
const loading = ref(false)
const box = ref(null)
const abortController = ref(null)

const username = localStorage.getItem('username') || 'admin'
const userInitial = username.slice(0, 1).toUpperCase()

const suggestions = [
  '找 3 个会 Python 的前端',
  '推荐有大模型项目经验的后端',
  '筛本科以上、3 年经验的算法工程师',
]

async function send(preset) {
  const text = (typeof preset === 'string' ? preset : input.value).trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  await run(text)
}

async function run(text) {
  loading.value = true
  // 预留一条助手消息，流式内容逐步追加进去
  const idx = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })
  const ctrl = new AbortController()
  abortController.value = ctrl
  scroll()
  try {
    await chatStream(text, {
      signal: ctrl.signal,
      onDelta: (chunk) => {
        if (messages.value[idx]) messages.value[idx].content += chunk
        scroll()
      },
      onTrace: (trace) => emit('result', trace),
    })
    const m = messages.value[idx]
    if (m && !m.content) m.content = '（无回答）'
  } catch (e) {
    const m = messages.value[idx]
    if (e.name === 'AbortError') {
      if (m && !m.content) m.content = '已停止生成。'
    } else if (m) {
      m.content = (m.content ? m.content + '\n\n' : '') + '出错了：' + e.message
      m.failed = true
      m.retryText = text
      toast('生成失败，可重试', 'error')
    }
  } finally {
    loading.value = false
    abortController.value = null
    scroll()
  }
}

function stop() {
  if (abortController.value) abortController.value.abort()
}

function retry(i) {
  const m = messages.value[i]
  if (!m || !m.retryText || loading.value) return
  const text = m.retryText
  messages.value.splice(i, 1)
  run(text)
}

async function clearChat() {
  if (loading.value || !messages.value.length) return
  const ok = await confirmAction({
    title: '清空当前对话？',
    message: '将同时重置服务端会话，AI 不再记得前面讨论过的需求。',
    confirmText: '清空对话',
    danger: true,
  })
  if (!ok) return
  try {
    await api.chatReset()
    messages.value = []
    toast('对话已清空', 'success')
  } catch (e) {
    toast(e.message || '清空失败', 'error')
  }
}

function onEsc(e) {
  if (e.key === 'Escape' && loading.value) stop()
}

window.addEventListener('keydown', onEsc)
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEsc)
  if (abortController.value) abortController.value.abort()
})

function scroll() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}
</script>

<style scoped>
.agent {
  height: 100%;
  min-height: 0;
}

.chat-head {
  padding: 15px 18px;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-tools {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 10px;
  background: linear-gradient(150deg, #17233d, #0d1729);
  color: #a8c0ff;
}

.live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 9px;
  border: 1px solid var(--green-soft);
  border-radius: 999px;
  background: #f3fbf8;
  font-size: 11px;
  font-weight: 600;
  color: var(--green);
}

.live i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse-soft 2.4s ease-in-out infinite;
}

.msgs {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 14px;
  min-height: 0;
  padding: 20px 18px;
  background: linear-gradient(180deg, #fbfcff 0%, #f7f9fd 100%);
}

/* 空状态 */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: auto;
  padding: 12px;
  text-align: center;
}

.chat-empty-mark {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  margin-bottom: 14px;
  border-radius: 17px;
  background: linear-gradient(150deg, #16223a, #0c1626);
  color: #a8c0ff;
  box-shadow: 0 14px 28px -16px rgba(13, 26, 48, 0.7);
}

.chat-empty h4 {
  font-size: 15px;
  font-weight: 700;
}

.chat-empty p {
  max-width: 260px;
  margin-top: 5px;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-3);
}

.suggests {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  margin-top: 20px;
}

.suggest {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  font-size: 12.5px;
  color: var(--text-2);
  text-align: left;
  transition: border-color 0.18s, color 0.18s, box-shadow 0.18s, transform 0.12s;
}

.suggest span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggest .icon {
  color: var(--brand);
  opacity: 0.7;
}

.suggest:hover {
  border-color: var(--brand-line);
  color: var(--brand-strong);
  box-shadow: var(--shadow-xs);
  transform: translateX(2px);
}

/* 消息 */
.msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  max-width: 100%;
}

.msg-row.user {
  flex-direction: row;
  justify-content: flex-end;
}

.msg-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
  max-width: 78%;
}

.msg-row.user .msg-body {
  align-items: flex-end;
}

.msg-avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  flex: none;
  border-radius: 9px;
  font-size: 11.5px;
  font-weight: 700;
}

.msg-avatar.ai {
  background: linear-gradient(150deg, #17233d, #0d1729);
  color: #a8c0ff;
}

.msg-avatar.me {
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.bubble {
  max-width: 100%;
  padding: 11px 14px;
  border-radius: 14px 14px 14px 4px;
  background: #fff;
  border: 1px solid var(--line);
  box-shadow: var(--shadow-xs);
  font-size: 13.5px;
  line-height: 1.72;
  white-space: pre-wrap;
  word-break: break-word;
  animation: rise 0.25s ease both;
}

.msg-row.user .bubble {
  border: none;
  border-radius: 14px 14px 4px 14px;
  background: linear-gradient(135deg, #2f63f0, #1a3fbd);
  color: #fff;
  box-shadow: 0 10px 22px -14px rgba(36, 86, 230, 0.9);
}

.bubble.failed {
  border-color: #f1d5d5;
  background: #fffafa;
}

.bubble.typing {
  padding: 14px;
}

.retry {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 26px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-3);
  transition: border-color 0.18s, color 0.18s;
}

.retry:hover {
  border-color: var(--brand-line);
  color: var(--brand-strong);
}

.dots {
  display: flex;
  gap: 4px;
}

.dots i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #9aa6bd;
  animation: blink 1.2s ease-in-out infinite;
}

.dots i:nth-child(2) {
  animation-delay: 0.16s;
}

.dots i:nth-child(3) {
  animation-delay: 0.32s;
}

@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-2px);
  }
}

/* 输入区 */
.composer {
  padding: 14px 16px 12px;
  border-top: 1px solid var(--line-soft);
  background: #fff;
}

.composer-box {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 5px 5px 14px;
  border: 1.5px solid var(--line);
  border-radius: 14px;
  background: #fafbfe;
  transition: border-color 0.18s, box-shadow 0.18s, background 0.18s;
}

.composer-box:focus-within {
  border-color: var(--brand);
  background: #fff;
  box-shadow: 0 0 0 4px rgba(36, 86, 230, 0.09);
}

.composer-box input {
  flex: 1;
  min-width: 0;
  height: 34px;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13.5px;
}

.composer-box input::placeholder {
  color: #a2abbd;
}

.send-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: none;
  border-radius: 10px;
  background: var(--brand);
  color: #fff;
  transition: background 0.18s, opacity 0.18s, transform 0.12s;
}

.send-btn:hover:not(:disabled) {
  background: var(--brand-strong);
}

.send-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.send-btn:disabled {
  background: #d7dcea;
  color: #fff;
  cursor: not-allowed;
}

.send-btn.stop {
  background: #fff;
  border: 1.5px solid var(--line);
  color: var(--text-2);
}

.send-btn.stop:hover {
  border-color: #f0c9c9;
  background: var(--red-soft);
  color: var(--red);
}

.composer-hint {
  margin-top: 7px;
  padding-left: 4px;
  font-size: 10.5px;
  color: #a3acbd;
}
</style>
