<!-- views/DeliveriesView.vue — o ecrã do recurso Delivery (Diogo).
     Cliente: acompanha as entregas das suas encomendas (a API só lhe devolve essas).
     Gestor: vê todas, expede (agendada → em trânsito) e conclui (em trânsito → entregue).
     O estado e a página vivem no URL (?status=in_transit&page=2). -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import StatusBadge, { type Tone } from '@/components/StatusBadge.vue'
import { useFetch } from '@/composables/useFetch'
import { useAuth } from '@/stores/auth'
import type { Delivery, DeliveryStatus } from '@/types'
import { dateTime } from '@/utils/format'

const PAGE_SIZE = 20

const TONE: Record<DeliveryStatus, Tone> = {
  scheduled: 'info',
  in_transit: 'neutral',
  delivered: 'ok',
}
const LABEL: Record<DeliveryStatus, string> = {
  scheduled: 'Agendada',
  in_transit: 'Em trânsito',
  delivered: 'Entregue',
}

const auth = useAuth()
const route = useRoute()
const router = useRouter()

function isStatus(value: unknown): value is DeliveryStatus {
  return typeof value === 'string' && value in LABEL
}
const statusFilter = computed({
  get: (): DeliveryStatus | '' => (isStatus(route.query.status) ? route.query.status : ''),
  set: (value: DeliveryStatus | '') =>
    void router.push({ query: { ...route.query, status: value || undefined, page: undefined } }),
})
const page = computed(() => {
  const n = Number(route.query.page)
  return Number.isInteger(n) && n > 0 ? n : 1
})
function goTo(n: number) {
  void router.push({ query: { ...route.query, page: n > 1 ? String(n) : undefined } })
}

const { data, status, error, reload } = useFetch(() =>
  unwrap(
    api.GET('/api/v1/deliveries/', {
      params: { query: { status: statusFilter.value || undefined, page: page.value } },
    }),
  ),
)
const deliveries = computed(() => data.value?.results ?? [])
const pages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / PAGE_SIZE)))

// ---- ações do gestor ----
const busy = ref<number | null>(null)
const rowError = reactive<Record<number, string | null>>({})

async function advance(delivery: Delivery, step: 'ship' | 'complete') {
  busy.value = delivery.id
  rowError[delivery.id] = null
  try {
    const params = { params: { path: { id: delivery.id } } }
    const updated = await unwrap(
      step === 'ship'
        ? api.POST('/api/v1/deliveries/{id}/ship/', params)
        : api.POST('/api/v1/deliveries/{id}/complete/', params),
    )
    if (data.value) {
      data.value.results = data.value.results.map((d) => (d.id === updated.id ? updated : d))
    }
  } catch (e) {
    rowError[delivery.id] = errorMessage(e) // 409: o estado já mudou noutra janela
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section>
    <header class="head">
      <h1>{{ auth.isGestor ? 'Entregas' : 'As minhas entregas' }}</h1>
      <RouterLink v-if="auth.isGestor" :to="{ name: 'new-delivery' }">Agendar entrega</RouterLink>
    </header>

    <label class="filter">
      Estado
      <select v-model="statusFilter" name="status">
        <option value="">Todos</option>
        <option v-for="(label, value) in LABEL" :key="value" :value="value">{{ label }}</option>
      </select>
    </label>

    <AsyncState
      :status="status"
      :error="error"
      :empty="deliveries.length === 0"
      :empty-text="
        auth.isGestor
          ? 'Não há entregas com este estado.'
          : 'Ainda não há entregas. Aparecem aqui quando uma encomenda paga é agendada.'
      "
      @retry="reload"
    >
      <table>
        <thead>
          <tr>
            <th scope="col">Encomenda</th>
            <th scope="col">Estado</th>
            <th scope="col">Data prevista</th>
            <th scope="col">Morada</th>
            <th v-if="auth.isGestor" scope="col">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in deliveries" :key="d.id">
            <td>#{{ d.order }}</td>
            <td><StatusBadge :label="d.status_display" :tone="TONE[d.status]" /></td>
            <td>
              {{ dateTime(d.scheduled_for) }}
              <small v-if="d.delivered_at">entregue {{ dateTime(d.delivered_at) }}</small>
            </td>
            <td>{{ d.address }}</td>
            <td v-if="auth.isGestor">
              <button
                v-if="d.status === 'scheduled'"
                type="button"
                :disabled="busy === d.id"
                @click="advance(d, 'ship')"
              >
                Expedir
              </button>
              <button
                v-else-if="d.status === 'in_transit'"
                type="button"
                :disabled="busy === d.id"
                @click="advance(d, 'complete')"
              >
                Concluir
              </button>
              <span v-else class="muted">—</span>
              <p v-if="rowError[d.id]" role="alert" class="field-error">{{ rowError[d.id] }}</p>
            </td>
          </tr>
        </tbody>
      </table>

      <nav v-if="pages > 1" class="pager" aria-label="Páginas">
        <button type="button" :disabled="!data?.previous" @click="goTo(page - 1)">Anterior</button>
        <span>Página {{ page }} de {{ pages }}</span>
        <button type="button" :disabled="!data?.next" @click="goTo(page + 1)">Seguinte</button>
      </nav>
    </AsyncState>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.filter {
  display: inline-grid;
  gap: 0.25rem;
  margin-bottom: 1rem;
}
table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}
th,
td {
  padding: 0.5rem;
  border-bottom: 1px solid #eee;
  text-align: left;
  vertical-align: top;
}
small {
  display: block;
  color: #666;
}
.muted {
  color: #888;
}
.field-error {
  margin: 0.25rem 0 0;
  color: #b00020;
  font-size: 0.9rem;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1rem;
}
</style>
