<!-- components/OrderStatusBadge.vue — o estado de uma encomenda, com um switch exaustivo. -->
<script setup lang="ts">
import { computed } from 'vue'

import type { OrderStatus } from '@/types'

const props = defineProps<{ status: OrderStatus }>()

const label = computed((): string => {
  switch (props.status) {
    case 'pending':
      return 'Por pagar'
    case 'paid':
      return 'Paga'
    case 'shipped':
      return 'Enviada'
    case 'cancelled':
      return 'Cancelada'
  }
  // Sem default: se a API ganhar um estado novo ('refunded') e o schema for regenerado,
  // aqui props.status deixa de ser `never` e o type-check falha — até o tratarmos.
  return props.status satisfies never
})
</script>

<template>
  <span class="badge" :class="props.status">{{ label }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  background: #eee;
}
.pending {
  background: #fff4d6;
  color: #7a5200;
}
.paid {
  background: #dff5e6;
  color: #1d6b3a;
}
.shipped {
  background: #e0ecff;
  color: #1f4b99;
}
.cancelled {
  background: #f3e0e0;
  color: #8a1f1f;
}
</style>
