<template>
  <svg
    class="icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    :fill="filled ? 'currentColor' : 'none'"
    :stroke="filled ? 'none' : 'currentColor'"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path v-for="(d, i) in icons[name] || []" :key="i" :d="d" />
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.7 },
})

const filled = computed(() => props.name === 'spark')

const icons = {
  spark: ['M12 2.4l2 6.1 6.1 2-6.1 2L12 18.6l-2-6.1-6.1-2 6.1-2L12 2.4Z'],
  workspace: [
    'M4.5 5.5A2.5 2.5 0 0 1 7 3h10a2.5 2.5 0 0 1 2.5 2.5v6.6a2.5 2.5 0 0 1-2.5 2.5h-7.2L5 19V5.5Z',
    'M8.5 8h7M8.5 11h5',
  ],
  board: ['M4 5.5h4v14H4zM10 5.5h4v9.5h-4zM16 5.5h4v12h-4z'],
  user: ['M12 11.5a3.9 3.9 0 1 0 0-7.8 3.9 3.9 0 0 0 0 7.8Z', 'M4.8 20.2a7.2 7.2 0 0 1 14.4 0'],
  lock: ['M6.5 10.5h11a1.5 1.5 0 0 1 1.5 1.5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 5 19v-7a1.5 1.5 0 0 1 1.5-1.5Z', 'M8.2 10.5V8a3.8 3.8 0 0 1 7.6 0v2.5', 'M12 15v2'],
  logout: ['M14.5 4.5H6.5A1.5 1.5 0 0 0 5 6v12a1.5 1.5 0 0 0 1.5 1.5h8', 'M10 12h10M17 9l3 3-3 3'],
  search: ['M11 18.5a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15Z', 'M16.6 16.6 21 21'],
  mail: [
    'M3 7.5A2.5 2.5 0 0 1 5.5 5h13A2.5 2.5 0 0 1 21 7.5v9A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z',
    'm3.6 7.2 8.4 6 8.4-6',
  ],
  sync: ['M20 11a8 8 0 0 0-14.7-4.4M4 13a8 8 0 0 0 14.7 4.4', 'M20 4v4.5h-4.5M4 20v-4.5h4.5'],
  filter: ['M4 6.5h16M7 12h10M10 17.5h4'],
  send: ['M21 3 10.6 13.4M21 3l-6.6 18-3.9-8.3L2.5 8.9 21 3Z'],
  stop: ['M9 9h6v6H9z'],
  refresh: ['M20 11.2a8 8 0 1 0-2.2 6.4', 'M20 5.2v6h-6'],
  more: ['M6 12h.01M12 12h.01M18 12h.01'],
  arrowLeft: ['M19.5 12H4.5M10.5 6 4.5 12l6 6'],
  arrowRight: ['M4.5 12h15M13.5 6l6 6-6 6'],
  edit: ['M4.5 19.5h4L19 9a2.8 2.8 0 0 0-4-4L4.5 15.5v4Z', 'm13.3 6.7 4 4'],
  trash: ['M4 7h16M9.5 7V5.2h5V7M6.5 7l.9 12.5h9.2L17.5 7', 'M10.5 10.5v6M13.5 10.5v6'],
  close: ['M6 6l12 12M18 6 6 18'],
  check: ['m5 12.8 4.4 4.4L19 7.6'],
  phone: [
    'M6.4 3.5h3l1.5 4-2 1.4a11.2 11.2 0 0 0 6.2 6.2l1.4-2 4 1.5v3a2 2 0 0 1-2 2C11.2 19.6 4.4 12.8 4.4 5.5a2 2 0 0 1 2-2Z',
  ],
  at: [
    'M16.2 12a4.2 4.2 0 1 1-8.4 0 4.2 4.2 0 0 1 8.4 0Z',
    'M16.2 7.8v4.4a2.5 2.5 0 0 0 5 0V12a9.2 9.2 0 1 0-3.7 7.4',
  ],
  cap: ['M2.6 9 12 4.6 21.4 9 12 13.4 2.6 9Z', 'M6.2 11v4.8c0 1.6 2.6 2.9 5.8 2.9s5.8-1.3 5.8-2.9V11'],
  briefcase: ['M3.5 8.5h17v10h-17z', 'M9 8.5V6.2h6v2.3', 'M3.5 13.2h17'],
  file: ['M6.2 3.2h7.6l4 4v13.6H6.2z', 'M13.8 3.2v4h4', 'M9 13h6M9 16.4h4'],
  clock: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 7.6V12l3.2 1.9'],
  alert: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 7.6v5.2M12 16.4h.01'],
  eye: ['M2.5 12S6 5.6 12 5.6 21.5 12 21.5 12 18 18.4 12 18.4 2.5 12 2.5 12Z', 'M12 14.8a2.8 2.8 0 1 0 0-5.6 2.8 2.8 0 0 0 0 5.6Z'],
  eyeOff: [
    'M2.5 12S6 5.6 12 5.6 21.5 12 21.5 12 18 18.4 12 18.4 2.5 12 2.5 12Z',
    'M12 14.8a2.8 2.8 0 1 0 0-5.6 2.8 2.8 0 0 0 0 5.6Z',
    'M3.4 3.4 20.6 20.6',
  ],
  chevronRight: ['m9.5 6 6 6-6 6'],
  plus: ['M12 5v14M5 12h14'],
  upload: ['M12 15.6V4.4M8 8.4 12 4.4l4 4', 'M4.2 15.6v3a1.8 1.8 0 0 0 1.8 1.8h12a1.8 1.8 0 0 0 1.8-1.8v-3'],
  inbox: [
    'M3.5 13.4 6 5.2h12l2.5 8.2v5.1a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5v-5.1Z',
    'M3.5 13.4h4.8l1.2 2.2h5l1.2-2.2h4.8',
  ],
}
</script>
