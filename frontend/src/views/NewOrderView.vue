<!-- views/NewOrderView.vue — um formulário que escreve: POST /orders/ e um POST /order-items/ por linha. -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api, ApiError, unwrap } from '@/api/client'
import { useFetch } from '@/composables/useFetch'

const router = useRouter()

// O catálogo para os <select>: a 1.ª página de produtos ativos (20).
const { data: catalogue, error: catalogueError } = useFetch(() =>
  unwrap(api.GET('/api/v1/products/', { params: { query: { is_active: true } } })),
)

interface Line {
  product: number | null // null = ainda não escolhido
  quantity: number
  error: string | null // a mensagem do serializer para ESTA linha
  saved: boolean // já foi gravada na API?
}

// As linhas são estado: objetos num só ref, com acrescentar e remover.
const lines = ref<Line[]>([{ product: null, quantity: 1, error: null, saved: false }])

function addLine() {
  lines.value.push({ product: null, quantity: 1, error: null, saved: false })
}
function removeLine(i: number) {
  lines.value.splice(i, 1)
}

// Total SÓ para mostrar (estimativa). O que conta é o da API, somado em Decimal.
// Em cêntimos inteiros, para não somar floats (0.1 + 0.2 = 0.30000000000000004).
const money = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' })
const total = computed(() => {
  let cents = 0
  for (const line of lines.value) {
    const p = catalogue.value?.results.find((x) => x.id === line.product)
    if (p) cents += Math.round(Number(p.price) * 100) * line.quantity
  }
  return cents / 100
})

const submitting = ref(false)
const formError = ref<string | null>(null) // erro geral, no topo
// Se uma linha falhar, a encomenda já existe: ao corrigir e reenviar, reutilizamo-la
// (e só enviamos as linhas que faltam) em vez de criar outra.
const orderId = ref<number | null>(null)

async function submit() {
  submitting.value = true
  formError.value = null
  for (const line of lines.value) line.error = null
  try {
    // Sem corpo: o customer vem do token e o status começa em pending — decide o servidor.
    orderId.value ??= (await unwrap(api.POST('/api/v1/orders/'))).id

    for (const line of lines.value) {
      if (line.saved) continue
      try {
        await unwrap(
          api.POST('/api/v1/order-items/', {
            body: { order: orderId.value, product: line.product ?? 0, quantity: line.quantity },
          }),
        )
        line.saved = true
      } catch (e) {
        if (e instanceof ApiError && e.status === 400) {
          // O veredicto do serializer, ao lado do campo que perguntou.
          line.error = e.field('quantity') ?? e.field('product') ?? e.detail
        } else {
          throw e
        }
      }
    }

    if (!lines.value.some((l) => l.error)) {
      await router.push({ name: 'orders' })
    }
  } catch (e) {
    formError.value = e instanceof ApiError ? e.detail : 'Erro de rede (a API está a correr?)'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'orders' }">‹ As minhas encomendas</RouterLink>
    <h1>Nova encomenda</h1>

    <p v-if="catalogueError" class="error">{{ catalogueError }}</p>
    <p v-if="formError" role="alert" class="error">{{ formError }}</p>
    <p v-if="orderId" class="note">
      A encomenda #{{ orderId }} já foi criada; corrige as linhas assinaladas e volta a enviar.
    </p>

    <form @submit.prevent="submit">
      <div
        v-for="(line, i) in lines"
        :key="i"
        class="row"
        :class="{ invalid: line.error, saved: line.saved }"
      >
        <select v-model="line.product" required :disabled="line.saved" aria-label="Produto">
          <option :value="null" disabled>Escolhe um produto…</option>
          <!-- Esgotados ficam visíveis mas não se podem escolher. O stock a sério continua a
               ser verificado pela API (pode esgotar entre carregar a página e enviar). -->
          <option
            v-for="p in catalogue?.results ?? []"
            :key="p.id"
            :value="p.id"
            :disabled="(p.stock ?? 0) === 0"
          >
            {{ p.name }} — {{ p.price }} €
            {{ (p.stock ?? 0) === 0 ? '(esgotado)' : `(${p.stock} em stock)` }}
          </option>
        </select>
        <input
          v-model.number="line.quantity"
          type="number"
          min="1"
          required
          :disabled="line.saved"
          aria-label="Quantidade"
        />
        <button type="button" :disabled="lines.length === 1 || line.saved" @click="removeLine(i)">
          Remover
        </button>
        <span v-if="line.saved" class="ok">✓ gravada</span>
        <p v-if="line.error" class="field-error">{{ line.error }}</p>
      </div>

      <button type="button" @click="addLine">+ Linha</button>
      <p class="total">Total (estimativa): {{ money.format(total) }}</p>
      <button type="submit" :disabled="submitting">
        {{ submitting ? 'A enviar…' : 'Criar encomenda' }}
      </button>
    </form>
  </section>
</template>

<style scoped>
form {
  display: grid;
  gap: 0.75rem;
  max-width: 40rem;
}
.row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}
.row.invalid {
  border-color: #b00020;
}
.row.saved {
  opacity: 0.7;
}
select {
  flex: 1;
  padding: 0.4rem;
}
input[type='number'] {
  width: 5rem;
  padding: 0.4rem;
}
.field-error {
  flex-basis: 100%;
  margin: 0;
  color: #b00020;
  font-size: 0.9rem;
}
.ok {
  color: #1d6b3a;
}
.total {
  font-weight: 600;
}
.note {
  color: #7a5200;
}
.error {
  color: #b00020;
}
</style>
