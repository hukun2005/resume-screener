<template>
  <article
    class="cand"
    tabindex="0"
    @click="$emit('click')"
    @keydown.enter="$emit('click')"
  >
    <span class="avatar cand-avatar" :style="avatarStyle">{{ initial }}</span>

    <div class="cand-main">
      <div class="cand-top">
        <h3>{{ c.name }}</h3>
        <span v-if="c.expected_position" class="pos">{{ c.expected_position }}</span>
      </div>

      <div v-if="skillList.length" class="tags">
        <span v-for="s in skillList" :key="s" class="tag">{{ s }}</span>
      </div>

      <p v-if="c.experience" class="exp">{{ c.experience }}</p>

      <p v-if="c.interview_at" class="iv-line">
        <AppIcon name="clock" :size="12" />
        <span>{{ ivText }}</span>
        <em v-if="modeLabel">· {{ modeLabel }}</em>
        <em v-if="c.interviewer">· {{ c.interviewer }}</em>
      </p>

      <p v-if="c.match_reason" class="reason">
        <AppIcon name="spark" :size="12" />
        <span>{{ c.match_reason }}</span>
      </p>
    </div>

    <div v-if="c.match_score != null" class="score" :class="scoreTone">
      <div class="score-ring" :style="{ '--p': c.match_score }">
        <span>{{ c.match_score }}<i>%</i></span>
      </div>
      <em>匹配</em>
    </div>

    <AppIcon name="chevronRight" :size="16" class="go" />
  </article>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { INTERVIEW_MODE_LABELS } from '../lib/flow.js'

const props = defineProps({ c: { type: Object, required: true } })
defineEmits(['click'])

const PALETTE = [
  ['#3f6df0', '#1a3fbd'],
  ['#7c5cf0', '#4a2fb0'],
  ['#12997a', '#07624c'],
  ['#c2811f', '#8a5608'],
  ['#cc4f87', '#93275a'],
  ['#2f8aa8', '#195a70'],
]

const initial = computed(() => (props.c.name || '?').trim().slice(0, 1))

const avatarStyle = computed(() => {
  const name = props.c.name || '?'
  let sum = 0
  for (const ch of name) sum += ch.charCodeAt(0)
  const [a, b] = PALETTE[sum % PALETTE.length]
  return { background: `linear-gradient(145deg, ${a}, ${b})`, color: '#fff' }
})

const skillList = computed(() =>
  (props.c.skills || '')
    .split(/[,，、/|]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 5),
)

const scoreTone = computed(() => {
  const s = props.c.match_score ?? 0
  if (s >= 80) return 'tone-high'
  if (s >= 60) return 'tone-mid'
  return 'tone-low'
})

const ivText = computed(() => {
  const v = props.c.interview_at
  if (!v) return ''
  const d = new Date(String(v).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(v).slice(5, 16)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
    d.getMinutes(),
  )}`
})

const modeLabel = computed(() => INTERVIEW_MODE_LABELS[props.c.interview_mode] || '')
</script>

<style scoped>
.cand {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 14px 14px 15px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.15s;
}

.cand:hover {
  border-color: var(--brand-line);
  box-shadow: 0 12px 26px -18px rgba(15, 26, 48, 0.45);
  transform: translateY(-1px);
}

.cand:focus-visible {
  outline: 2px solid var(--brand);
  outline-offset: 2px;
}

.cand-avatar {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  font-size: 14px;
}

.cand-main {
  flex: 1;
  min-width: 0;
}

.cand-top {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.cand-top h3 {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.pos {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border-radius: 5px;
  background: var(--brand-soft);
  color: var(--brand-strong);
  font-size: 11.5px;
  font-weight: 600;
}

.cand-main .tags {
  margin-top: 7px;
}

.exp {
  margin-top: 7px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-3);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.iv-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
  padding: 5px 8px;
  border-radius: 8px;
  background: #f4f1fe;
  color: #5a40c4;
  font-size: 11.5px;
  font-weight: 600;
}

.iv-line .icon {
  flex: none;
}

.iv-line span {
  font-variant-numeric: tabular-nums;
}

.iv-line em {
  font-style: normal;
  font-weight: 500;
  color: #7963d6;
}

.reason {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 9px;
  padding: 7px 9px;
  border-radius: 8px;
  background: #f5f8ff;
  border: 1px dashed #d7e1ff;
  color: var(--brand-strong);
  font-size: 11.5px;
  line-height: 1.6;
}

.reason .icon {
  flex: none;
  margin-top: 2px;
  color: var(--brand);
}

.score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  flex: none;
  padding-top: 1px;
}

.score em {
  font-style: normal;
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--text-3);
}

.score-ring {
  position: relative;
  display: grid;
  place-items: center;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: conic-gradient(var(--tone) calc(var(--p) * 1%), #e9edf6 0);
}

.score-ring::before {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: #fff;
}

.score-ring span {
  position: relative;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--tone);
  font-variant-numeric: tabular-nums;
}

.score-ring i {
  font-style: normal;
  font-size: 9px;
  margin-left: 1px;
}

.tone-high {
  --tone: #0f8a68;
}

.tone-mid {
  --tone: #2456e6;
}

.tone-low {
  --tone: #b06d13;
}

.go {
  align-self: center;
  color: #c2c9d8;
  transition: color 0.18s, transform 0.18s;
}

.cand:hover .go {
  color: var(--brand);
  transform: translateX(2px);
}

@media (max-width: 560px) {
  .score {
    display: none;
  }

  .go {
    display: none;
  }
}
</style>
