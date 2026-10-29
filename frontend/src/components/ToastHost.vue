<template>
  <div class="toast-host" role="status" aria-live="polite">
    <transition-group name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        :class="['toast', 't-' + t.type]"
      >
        <span class="toast-ico">
          <AppIcon :name="iconOf(t.type)" :size="15" />
        </span>
        <p class="toast-text">{{ t.message }}</p>
        <button class="toast-close" type="button" aria-label="关闭提示" @click="dismissToast(t.id)">
          <AppIcon name="close" :size="13" />
        </button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { toasts, dismissToast } from '../lib/ui.js'
import AppIcon from './AppIcon.vue'

function iconOf(type) {
  if (type === 'success') return 'check'
  if (type === 'error') return 'alert'
  return 'spark'
}
</script>

<style scoped>
.toast-host {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 120;
  display: flex;
  flex-direction: column;
  gap: 9px;
  width: min(330px, calc(100vw - 32px));
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  padding: 11px 10px 11px 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  box-shadow: var(--shadow);
  pointer-events: auto;
}

.toast-ico {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  flex: none;
  border-radius: 8px;
  background: var(--brand-soft);
  color: var(--brand-strong);
}

.toast-text {
  flex: 1;
  padding-top: 1px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-2);
  word-break: break-word;
}

.toast-close {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex: none;
  border-radius: 6px;
  color: #9aa4b8;
  transition: background 0.18s, color 0.18s;
}

.toast-close:hover {
  background: #f1f3f8;
  color: var(--text-2);
}

.toast.t-success .toast-ico {
  background: var(--green-soft);
  color: var(--green);
}

.toast.t-error .toast-ico {
  background: var(--red-soft);
  color: var(--red);
}

.toast.t-error {
  border-color: #f3d4d4;
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.98);
}

.toast-leave-active {
  position: absolute;
  right: 0;
  width: 100%;
}

@media (max-width: 620px) {
  .toast-host {
    top: 12px;
    right: 12px;
    left: 12px;
    width: auto;
  }
}
</style>
