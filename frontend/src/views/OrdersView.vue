<!-- views/OrdersView.vue — as minhas encomendas. É a API que filtra: um cliente só recebe as suas. -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, ApiError, unwrap } from '@/api/client'
import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import { useFetch } from '@/composables/useFetch'
import type { Order } from '@/types'

const route = useRoute()
const router = useRouter()

const page = computed(() => Number(route.query.page ?? 1))

const { data, status, error, reload } = useFetch(() =>
  unwrap(
    api.GET('/api/v1/orders/', {
      params: { query: { page: page.value > 1 ? page.value : undefined } },
    }),
  ),
)

function goTo(n: number) {
  router.push({ query: { ...route.query, page: n > 1 ? n : undefined } })
}

// Pagar: o resultado (ou o 409) aparece como mensagem por cima da lista — não como ecrã de erro.
const paying = ref<number | null>(null)
const message = ref<string | null>(null)

async function pay(order: Order) {
  paying.value = order.id
  message.value = null
  try {
    await unwrap(api.POST('/api/v1/orders/{id}/pay/', { params: { path: { id: order.id } } }))
    message.value = `Encomenda #${order.id} paga.`
  } catch (e) {
    // 409: o estado mudou entretanto (ex.: paga noutro separador). A mensagem é da API.
    message.value = e instanceof ApiError ? e.detail : 'Erro de rede.'
  } finally {
    paying.value = null
    void reload() // em ambos os casos, mostrar o estado verdadeiro
  }
}

const date = (iso: string) => new Date(iso).toLocaleString('pt-PT')
</script>

<template>
  <section>
    <div class="head">
      <h1>As minhas encomendas</h1>
      <RouterLink :to="{ name: 'new-order' }" class="new">+ Nova encomenda</RouterLink>
    </div>

    <p v-if="message" role="status" class="message">{{ message }}</p>

    <p v-if="status === 'loading' && !data">A carregar…</p>
    <p v-else-if="status === 'error'" class="error">
      {{ error }} <button type="button" @click="reload">Tentar outra vez</button>
    </p>
    <template v-else-if="data">
      <!-- estado vazio: diz o que se passa e oferece a ação -->
      <p v-if="data.count === 0">
        Ainda sem encomendas.
        <RouterLink :to="{ name: 'new-order' }">Fazer a primeira</RouterLink>
      </p>
      <template v-else>
        <p class="summary">
          {{ data.count }} encomendas · página {{ page }}
          <span v-if="status === 'loading'"> · a atualizar…</span>
        </p>
        <ul class="orders">
          <li v-for="order in data.results" :key="order.id" class="order">
            <div class="line">
              <strong>#{{ order.id }}</strong>
              <OrderStatusBadge :status="order.status" />
              <span class="when">{{ date(order.created_at) }}</span>
              <span class="total">{{ order.total ?? '0.00' }} €</span>
              <button
                v-if="order.status === 'pending'"
                type="button"
                :disabled="paying === order.id"
                @click="pay(order)"
              >
                {{ paying === order.id ? 'A pagar…' : 'Pagar' }}
              </button>
            </div>
            <ul class="items">
              <li v-for="item in order.items" :key="item.id">
                {{ item.quantity }} × {{ item.product_name }} ({{ item.unit_price }} €)
              </li>
            </ul>
          </li>
        </ul>
        <nav class="pager">
          <button type="button" :disabled="!data.previous" @click="goTo(page - 1)">
            ‹ Anterior
          </button>
          <button type="button" :disabled="!data.next" @click="goTo(page + 1)">Seguinte ›</button>
        </nav>
      </template>
    </template>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.message {
  padding: 0.5rem 0.75rem;
  border-left: 4px solid #42b883;
  background: #f3faf6;
}
.summary,
.when {
  color: #6b6b6b;
}
.orders {
  list-style: none;
  padding: 0;
  display: grid;
  gap: 0.75rem;
}
.order {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
.line {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.total {
  margin-left: auto;
  font-weight: 600;
}
.items {
  margin: 0.5rem 0 0;
  padding-left: 1.25rem;
  color: #444;
  font-size: 0.9rem;
}
.pager {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
}
.error {
  color: #b00020;
}
</style>
