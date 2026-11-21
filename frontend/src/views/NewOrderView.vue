<!-- views/NewOrderView.vue — criar uma encomenda com várias linhas num só pedido:
     POST /orders/ {"items": [{"car": 1, "quantity": 2}, …]} (o M1 cria tudo numa transação).
     Os erros chegam por linha (errors.items["1"].car) ou da lista toda (errors.items). -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import { useFetch } from '@/composables/useFetch'
import type { Car } from '@/types'
import { money } from '@/utils/format'

type Line = { car: number | null; quantity: number }

const route = useRoute()
const router = useRouter()

// O catálogo para escolher: todas as viaturas à venda (vêm em páginas de 20).
const {
  data: cars,
  status,
  error,
  reload,
} = useFetch(async () => {
  const all: Car[] = []
  for (let page = 1; page <= 10; page++) {
    const result = await unwrap(
      api.GET('/api/v1/cars/', { params: { query: { is_active: true, page } } }),
    )
    all.push(...result.results)
    if (!result.next) break
  }
  return all
})
const byId = computed(() => new Map((cars.value ?? []).map((car) => [car.id, car])))

// ?car=7 (vindo do detalhe da viatura) começa com essa viatura escolhida.
const first = Number(route.query.car)
const lines = reactive<Line[]>([
  { car: Number.isInteger(first) && first > 0 ? first : null, quantity: 1 },
])

function addLine() {
  lines.push({ car: null, quantity: 1 })
}
function removeLine(index: number) {
  lines.splice(index, 1)
  lineErrors.value = {} // os índices mudaram: os erros antigos já não batem certo
}

const total = computed(() =>
  lines.reduce((sum, line) => {
    const car = line.car === null ? undefined : byId.value.get(line.car)
    return car ? sum + Number(car.price) * line.quantity : sum
  }, 0),
)

// ---- submeter ----
const submitting = ref(false)
const lineErrors = ref<Record<number, Record<string, string>>>({})
const listError = ref<string | null>(null)

async function submit() {
  submitting.value = true
  lineErrors.value = {}
  listError.value = null
  try {
    const order = await unwrap(
      api.POST('/api/v1/orders/', {
        // Uma linha sem viatura vai como car: 0 → a API responde com o erro nessa linha.
        body: { items: lines.map((l) => ({ car: l.car ?? 0, quantity: l.quantity })) },
      }),
    )
    await router.push({ name: 'orders', query: { status: 'pending', created: String(order.id) } })
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      lineErrors.value = e.lines('items')
      listError.value = e.field('items') ?? (Object.keys(lineErrors.value).length ? null : e.detail)
    } else {
      listError.value = errorMessage(e) // 409: alguém comprou a última unidade entretanto
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <h1>Nova encomenda</h1>

    <AsyncState :status="status" :error="error" @retry="reload">
      <form novalidate @submit.prevent="submit">
        <fieldset v-for="(line, i) in lines" :key="i" class="line">
          <legend>Linha {{ i + 1 }}</legend>
          <label>
            Viatura
            <select
              v-model="line.car"
              :name="`car-${i}`"
              :aria-invalid="Boolean(lineErrors[i]?.car)"
            >
              <option :value="null" disabled>Escolher…</option>
              <option v-for="car in cars" :key="car.id" :value="car.id">
                {{ car.brand_name }} {{ car.model }} {{ car.version }} —
                {{ money(car.price) }} (stock {{ car.stock }})
              </option>
            </select>
          </label>
          <p v-if="lineErrors[i]?.car" class="field-error">{{ lineErrors[i]?.car }}</p>

          <label>
            Quantidade
            <input
              v-model.number="line.quantity"
              :name="`quantity-${i}`"
              type="number"
              min="1"
              :aria-invalid="Boolean(lineErrors[i]?.quantity)"
            />
          </label>
          <p v-if="lineErrors[i]?.quantity" class="field-error">{{ lineErrors[i]?.quantity }}</p>

          <button v-if="lines.length > 1" type="button" class="remove" @click="removeLine(i)">
            Remover linha
          </button>
        </fieldset>

        <button type="button" @click="addLine">+ Adicionar linha</button>

        <p class="total">Total estimado: {{ money(total) }}</p>
        <p v-if="listError" role="alert" class="field-error">{{ listError }}</p>
        <button type="submit" :disabled="submitting">
          {{ submitting ? 'A criar…' : 'Criar encomenda' }}
        </button>
      </form>
    </AsyncState>
  </section>
</template>

<style scoped>
form {
  display: grid;
  gap: 0.75rem;
  max-width: 36rem;
}
.line {
  display: grid;
  gap: 0.4rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.line label {
  display: grid;
  gap: 0.25rem;
}
.remove {
  justify-self: start;
}
.total {
  margin: 0;
  font-weight: 700;
}
.field-error {
  margin: 0;
  color: #b00020;
  font-size: 0.9rem;
}
</style>
