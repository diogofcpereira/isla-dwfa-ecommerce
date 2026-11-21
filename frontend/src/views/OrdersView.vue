<!-- views/OrdersView.vue — "as minhas encomendas" (o gestor vê todas): pagar ou apagar as
     pendentes. O estado e a página vivem no URL (?status=pending&page=2). -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import StatusBadge, { type Tone } from '@/components/StatusBadge.vue'
import { useFetch } from '@/composables/useFetch'
import { useAuth } from '@/stores/auth'
import type { Order, OrderStatus, PaymentMethod } from '@/types'
import { dateTime, money } from '@/utils/format'

const PAGE_SIZE = 20

// Exaustivos: um estado ou método novo no schema deixa de compilar até ser tratado aqui.
const STATUS: Record<OrderStatus, { label: string; tone: Tone }> = {
  pending: { label: 'Pendente', tone: 'info' },
  paid: { label: 'Paga', tone: 'ok' },
  delivered: { label: 'Entregue', tone: 'ok' },
  cancelled: { label: 'Cancelada', tone: 'bad' },
}
const METHODS: Record<PaymentMethod, string> = {
  transfer: 'Transferência',
  financing: 'Financiamento',
  card: 'Cartão',
  mbway: 'MB WAY',
}

const auth = useAuth()
const route = useRoute()
const router = useRouter()

function isStatus(value: unknown): value is OrderStatus {
  return typeof value === 'string' && value in STATUS
}

const statusFilter = computed({
  get: (): OrderStatus | '' => (isStatus(route.query.status) ? route.query.status : ''),
  set: (value: OrderStatus | '') =>
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
    api.GET('/api/v1/orders/', {
      params: { query: { status: statusFilter.value || undefined, page: page.value } },
    }),
  ),
)
const orders = computed(() => data.value?.results ?? [])
const pages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / PAGE_SIZE)))

// ---- ações numa encomenda pendente ----
const method = reactive<Record<number, PaymentMethod>>({}) // o método escolhido em cada linha
const busy = ref<number | null>(null) // o id da encomenda em curso (desativa os botões dela)
const rowError = reactive<Record<number, string | null>>({})
const notice = ref<string | null>(null)

function replace(updated: Order) {
  if (!data.value) return
  data.value.results = data.value.results.map((o) => (o.id === updated.id ? updated : o))
}

async function pay(order: Order) {
  const chosen = method[order.id]
  if (!chosen) return // o botão está desativado até se escolher um método
  busy.value = order.id
  rowError[order.id] = null
  notice.value = null
  try {
    const paid = await unwrap(
      api.POST('/api/v1/orders/{id}/pay/', {
        params: { path: { id: order.id } },
        body: { method: chosen },
      }),
    )
    replace(paid)
    notice.value = `Encomenda #${order.id} paga (${money(paid.total)}).`
  } catch (e) {
    // 409: outra janela já a pagou; 400: método inválido. A mensagem vem da API.
    rowError[order.id] =
      e instanceof ApiError && e.status === 400 ? (e.field('method') ?? e.detail) : errorMessage(e)
  } finally {
    busy.value = null
  }
}

async function remove(order: Order) {
  busy.value = order.id
  rowError[order.id] = null
  notice.value = null
  try {
    const { response, error: problem } = await api.DELETE('/api/v1/orders/{id}/', {
      params: { path: { id: order.id } },
    })
    if (!response.ok) throw new ApiError(response.status, problem ?? null)
    notice.value = `Encomenda #${order.id} apagada; as viaturas voltaram ao stock.`
    await reload()
  } catch (e) {
    rowError[order.id] = errorMessage(e)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section>
    <header class="head">
      <h1>{{ auth.isGestor ? 'Encomendas' : 'As minhas encomendas' }}</h1>
    </header>

    <label class="filter">
      Estado
      <select v-model="statusFilter" name="status">
        <option value="">Todos</option>
        <option v-for="(s, value) in STATUS" :key="value" :value="value">{{ s.label }}</option>
      </select>
    </label>

    <p v-if="notice" role="status" class="notice">{{ notice }}</p>

    <AsyncState
      :status="status"
      :error="error"
      :empty="orders.length === 0"
      empty-text="Ainda não há encomendas aqui."
      @retry="reload"
    >
      <article v-for="order in orders" :key="order.id" class="order">
        <header>
          <strong>#{{ order.id }}</strong>
          <StatusBadge :label="STATUS[order.status].label" :tone="STATUS[order.status].tone" />
          <span class="muted">{{ dateTime(order.created_at) }}</span>
          <span v-if="auth.isGestor" class="muted">cliente {{ order.customer }}</span>
          <span class="total">{{ money(order.total) }}</span>
        </header>
        <ul>
          <li v-for="line in order.items" :key="line.id">
            {{ line.quantity }} × {{ line.car_name }} — {{ money(line.unit_price) }}
          </li>
        </ul>

        <div v-if="order.status === 'pending'" class="actions">
          <label>
            Pagamento
            <select v-model="method[order.id]" :name="`method-${order.id}`">
              <option :value="undefined" disabled>Escolher…</option>
              <option v-for="(label, value) in METHODS" :key="value" :value="value">
                {{ label }}
              </option>
            </select>
          </label>
          <button
            type="button"
            :disabled="busy === order.id || !method[order.id]"
            @click="pay(order)"
          >
            Pagar
          </button>
          <button type="button" :disabled="busy === order.id" @click="remove(order)">Apagar</button>
        </div>
        <p v-if="rowError[order.id]" role="alert" class="field-error">
          {{ rowError[order.id] }}
        </p>
      </article>

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
.notice {
  color: #2c7a5b;
}
.order {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.order header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
.muted {
  color: #666;
  font-size: 0.9rem;
}
.total {
  margin-left: auto;
  font-weight: 700;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 0.5rem;
}
.actions label {
  display: grid;
  gap: 0.25rem;
}
.field-error {
  margin: 0.5rem 0 0;
  color: #b00020;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}
</style>
