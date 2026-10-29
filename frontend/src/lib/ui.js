import { reactive } from 'vue'

/* ------------------------------ Toast ------------------------------ */
export const toasts = reactive([])
let seq = 0

export function toast(message, type = 'info', duration = 3200) {
  const id = ++seq
  toasts.push({ id, message, type })
  if (duration > 0) setTimeout(() => dismissToast(id), duration)
  return id
}

export function dismissToast(id) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i > -1) toasts.splice(i, 1)
}

/* --------------------------- Confirm dialog ------------------------ */
export const confirmState = reactive({
  open: false,
  title: '确认操作',
  message: '',
  confirmText: '确认',
  cancelText: '取消',
  danger: false,
  resolve: null,
})

export function confirmAction({
  title = '确认操作',
  message = '',
  confirmText = '确认',
  cancelText = '取消',
  danger = false,
} = {}) {
  Object.assign(confirmState, { open: true, title, message, confirmText, cancelText, danger })
  return new Promise((resolve) => {
    confirmState.resolve = resolve
  })
}

export function settleConfirm(ok) {
  confirmState.open = false
  const resolve = confirmState.resolve
  confirmState.resolve = null
  if (resolve) resolve(ok)
}
