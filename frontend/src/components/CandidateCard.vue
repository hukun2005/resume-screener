<template>
  <div class="cand-card" @click="$emit('click')">
    <div class="cand-head">
      <span class="name">{{ c.name }}</span>
      <span v-if="c.match_score != null" class="score">{{ c.match_score }}%</span>
    </div>
    <p class="pos">{{ c.expected_position }}</p>
    <p class="skills">{{ c.skills }}</p>
    <p class="exp">{{ c.experience }}</p>
  </div>
</template>

<script setup>
defineProps({ c: { type: Object, required: true } })
defineEmits(['click'])
</script>

<style scoped>
.cand-card {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f1f6;
  cursor: pointer;
  transition: background 0.15s;
}

.cand-card:hover {
  background: #f6f9ff;
}

.cand-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.name {
  font-size: 16px;
  font-weight: 600;
}

.score {
  background: #eef4ff;
  color: #1a6fe0;
  font-weight: 700;
  font-size: 13px;
  padding: 2px 10px;
  border-radius: 12px;
}

.pos {
  color: #1a6fe0;
  font-size: 13px;
  margin: 4px 0;
}

.skills {
  color: #666;
  font-size: 13px;
}

.exp {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
}
</style>