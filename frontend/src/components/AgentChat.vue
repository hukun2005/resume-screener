<template>
  <div class="panel agent">
    <div class="panel-title">AI 筛选助手</div>
    <div class="msgs" ref="box">
      <div v-for="(m, i) in messages" :key="i" :class="['msg', m.role]">
        {{ m.content }}
      </div>
    </div>
    <div class="input-row">
      <input
        v-model="input"
        @keyup.enter="send"
        placeholder="例如：找 3 个会 Python 的前端"
      />
      <button class="btn" @click="send" :disabled="loading">发送</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { api, chatStream } from '../api.js'

const emit = defineEmits(['result'])
const messages = ref([])
const input = ref('')
const loading = ref(false)
const box = ref(null)

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return
  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  // 预留一条助手消息，流式内容逐步追加进去
  const idx = messages.value.length
  messages.value.push({ role: 'assistant', content: '' })
  scroll()
  try {
    await chatStream(text, {
      onDelta: (chunk) => {
        messages.value[idx].content += chunk
        scroll()
      },
      onTrace: (trace) => emit('result', trace),
    })
    if (!messages.value[idx].content) {
      messages.value[idx].content = '（无回答）'
    }
  } catch (e) {
    messages.value[idx].content = messages.value[idx].content || '出错了：' + e.message
  } finally {
    loading.value = false
    scroll()
  }
}

function scroll() {
  nextTick(() => {
    if (box.value) box.value.scrollTop = box.value.scrollHeight
  })
}
</script>

<style scoped>
.agent {
  width: 42%;
  flex-shrink: 0;
}

.msgs {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.msg {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg.user {
  align-self: flex-end;
  background: #1a6fe0;
  color: #fff;
}

.msg.assistant {
  align-self: flex-start;
  background: #f0f2f7;
  color: #222;
}

.input-row {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-top: 1px solid #e5e8f0;
}

.input-row input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #e5e8f0;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
}

.input-row input:focus {
  border-color: #1a6fe0;
}
</style>