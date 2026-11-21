<!-- components/StatusBadge.vue — o estado de uma encomenda, entrega, avaliação ou test drive.
     Cada ecrã decide o tom com um Record<…StatusEnum, Tone>: um estado novo na API
     deixa de compilar até alguém lhe dar um tom. -->
<script setup lang="ts">
export type Tone = 'neutral' | 'info' | 'ok' | 'bad'

defineProps<{ label: string; tone: Tone }>()
</script>

<template>
  <span class="badge" :class="tone">{{ label }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}
.neutral {
  background: #eee;
  color: #444;
}
.info {
  background: #e3f0fb;
  color: #1d5a8c;
}
.ok {
  background: #e2f4ea;
  color: #1f6b47;
}
.bad {
  background: #fbe5e8;
  color: #9b1c2e;
}
</style>
