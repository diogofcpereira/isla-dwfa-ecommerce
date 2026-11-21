<!-- components/AsyncState.vue — os 4 estados de um ecrã que carrega dados, num só sítio:
     a carregar · erro (com "Tentar de novo") · vazio · dados.
     Uso: <AsyncState :status :error :empty="lista.length === 0" @retry="reload"> …dados… </AsyncState> -->
<script setup lang="ts">
import type { Status } from '@/types'

defineProps<{
  status: Status
  error: string | null
  empty?: boolean
  emptyText?: string
}>()

defineEmits<{ retry: [] }>()
</script>

<template>
  <!-- aria-live: um leitor de ecrã anuncia "A carregar…" e o erro sem o utilizador procurar -->
  <div class="async" aria-live="polite">
    <p v-if="status === 'loading' || status === 'idle'" class="state loading">A carregar…</p>

    <div v-else-if="status === 'error'" class="state error" role="alert">
      <p>{{ error ?? 'Ocorreu um erro.' }}</p>
      <button type="button" @click="$emit('retry')">Tentar de novo</button>
    </div>

    <div v-else-if="empty" class="state empty">
      <slot name="empty">
        <p>{{ emptyText ?? 'Não há nada para mostrar.' }}</p>
      </slot>
    </div>

    <slot v-else />
  </div>
</template>

<style scoped>
.state {
  padding: 1.5rem;
  border: 1px dashed #ccc;
  border-radius: 6px;
  text-align: center;
  color: #555;
}
.error {
  border-color: #b00020;
  color: #b00020;
}
.state p {
  margin: 0 0 0.5rem;
}
</style>
