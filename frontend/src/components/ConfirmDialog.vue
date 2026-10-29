<template>
  <transition name="dlg">
    <div v-if="confirmState.open" class="mask" @click.self="cancel">
      <div
        ref="panel"
        class="dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="dlg-title"
        aria-describedby="dlg-msg"
        @keydown="onKeydown"
      >
        <div class="dlg-body">
          <span :class="['dlg-ico', { danger: confirmState.danger }]">
            <AppIcon :name="confirmState.danger ? 'alert' : 'file'" :size="19" />
          </span>
          <div class="dlg-copy">
            <h3 id="dlg-title">{{ confirmState.title }}</h3>
            <p v-if="confirmState.message" id="dlg-msg">{{ confirmState.message }}</p>
          </div>
        </div>
        <div class="dlg-actions">
          <button ref="cancelBtn" class="btn btn-ghost" type="button" @click="cancel">
            {{ confirmState.cancelText }}
          </button>
          <button
            ref="confirmBtn"
            :class="['btn', confirmState.danger ? 'btn-danger' : '']"
            type="button"
            @click="settleConfirm(true)"
          >
            {{ confirmState.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { confirmState, settleConfirm } from '../lib/ui.js'
import AppIcon from './AppIcon.vue'

const panel = ref(null)
const confirmBtn = ref(null)
const cancelBtn = ref(null)

let lastFocus = null
let prevOverflow = ''

watch(
  () => confirmState.open,
  (open) => {
    if (open) {
      lastFocus = document.activeElement
      prevOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      nextTick(() => confirmBtn.value && confirmBtn.value.focus())
    } else {
      document.body.style.overflow = prevOverflow
      if (lastFocus && typeof lastFocus.focus === 'function') lastFocus.focus()
      lastFocus = null
    }
  }
)

function cancel() {
  settleConfirm(false)
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    e.preventDefault()
    cancel()
    return
  }
  if (e.key !== 'Tab') return
  const items = [cancelBtn.value, confirmBtn.value].filter(Boolean)
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

onBeforeUnmount(() => {
  if (confirmState.open) document.body.style.overflow = prevOverflow
})
</script>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(10, 18, 34, 0.46);
  backdrop-filter: blur(2px);
}

.dialog {
  width: min(400px, 100%);
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

.dlg-body {
  display: flex;
  gap: 12px;
  padding: 20px 20px 16px;
}

.dlg-ico {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  flex: none;
  border-radius: 12px;
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.dlg-ico.danger {
  background: var(--red-soft);
  color: var(--red);
}

.dlg-copy {
  min-width: 0;
}

.dlg-copy h3 {
  font-size: 15px;
  font-weight: 700;
  line-height: 1.4;
  color: var(--text);
}

.dlg-copy p {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-3);
}

.dlg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 20px 18px;
  border-top: 1px solid var(--line-soft);
  background: #fbfcfe;
}

.dlg-enter-active,
.dlg-leave-active {
  transition: opacity 0.2s ease;
}

.dlg-enter-active .dialog,
.dlg-leave-active .dialog {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.dlg-enter-from,
.dlg-leave-to {
  opacity: 0;
}

.dlg-enter-from .dialog,
.dlg-leave-to .dialog {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
</style>
