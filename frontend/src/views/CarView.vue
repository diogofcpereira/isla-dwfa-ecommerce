<!-- views/CarView.vue — o detalhe de uma viatura (/cars/7).
     Para o gestor, um painel para mudar preço, stock e se está à venda (PATCH /cars/{id}/).
     O painel só aparece a gestores, mas quem decide é a API: um cliente leva 403. -->
<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import { useFetch } from '@/composables/useFetch'
import { useAuth } from '@/stores/auth'
import type { Car } from '@/types'
import { money } from '@/utils/format'

const props = defineProps<{ id: string }>() // vem do URL (props: true na rota)

const auth = useAuth()

const {
  data: car,
  status,
  error,
  reload,
} = useFetch(() =>
  unwrap(api.GET('/api/v1/cars/{id}/', { params: { path: { id: Number(props.id) } } })),
)

// ---- painel do gestor ----
const form = reactive({ price: '', stock: 0, is_active: true })
const saving = ref(false)
const saved = ref(false)
const fieldErrors = reactive<Record<'price' | 'stock' | 'is_active', string | null>>({
  price: null,
  stock: null,
  is_active: null,
})
const formError = ref<string | null>(null)

// Quando a viatura chega (ou muda), o formulário recomeça com os valores dela.
watch(car, (value: Car | null) => {
  if (!value) return
  form.price = value.price
  form.stock = value.stock ?? 0
  form.is_active = value.is_active ?? true
})

async function save() {
  saving.value = true
  saved.value = false
  formError.value = null
  fieldErrors.price = fieldErrors.stock = fieldErrors.is_active = null
  try {
    car.value = await unwrap(
      api.PATCH('/api/v1/cars/{id}/', {
        params: { path: { id: Number(props.id) } },
        body: { price: form.price, stock: form.stock, is_active: form.is_active },
      }),
    )
    saved.value = true
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      fieldErrors.price = e.field('price')
      fieldErrors.stock = e.field('stock')
      fieldErrors.is_active = e.field('is_active')
    } else {
      formError.value = errorMessage(e) // 403 (não é gestor), 404, rede…
    }
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'cars' }">← Voltar ao catálogo</RouterLink>

    <AsyncState :status="status" :error="error" @retry="reload">
      <template v-if="car">
        <h1>{{ car.brand_name }} {{ car.model }}</h1>
        <dl class="specs">
          <dt>Versão</dt>
          <dd>{{ car.version || '—' }}</dd>
          <dt>Ano</dt>
          <dd>{{ car.year }}</dd>
          <dt>Combustível</dt>
          <dd>{{ car.fuel_display }}</dd>
          <dt>Código</dt>
          <dd>{{ car.code }}</dd>
          <dt>Preço</dt>
          <dd class="price">{{ money(car.price) }}</dd>
          <dt>Stock</dt>
          <dd>{{ car.stock }}</dd>
        </dl>
        <p v-if="car.is_active === false" class="warn">Esta viatura não está à venda.</p>

        <RouterLink
          v-if="auth.isLoggedIn && car.is_active && (car.stock ?? 0) > 0"
          :to="{ name: 'new-order', query: { car: car.id } }"
          class="buy"
        >
          Encomendar esta viatura
        </RouterLink>

        <!-- Só para gestores. A API repete a regra (IsGestorOrReadOnly): esconder não protege. -->
        <form v-if="auth.isGestor" class="panel" novalidate @submit.prevent="save">
          <h2>Gestão</h2>
          <label>
            Preço (€)
            <input
              v-model="form.price"
              name="price"
              inputmode="decimal"
              :aria-invalid="fieldErrors.price !== null"
              aria-describedby="price-error"
            />
          </label>
          <p v-if="fieldErrors.price" id="price-error" class="field-error">
            {{ fieldErrors.price }}
          </p>

          <label>
            Stock
            <input
              v-model.number="form.stock"
              name="stock"
              type="number"
              min="0"
              :aria-invalid="fieldErrors.stock !== null"
              aria-describedby="stock-error"
            />
          </label>
          <p v-if="fieldErrors.stock" id="stock-error" class="field-error">
            {{ fieldErrors.stock }}
          </p>

          <label class="check">
            <input v-model="form.is_active" name="is_active" type="checkbox" />
            À venda
          </label>
          <p v-if="fieldErrors.is_active" class="field-error">{{ fieldErrors.is_active }}</p>

          <p v-if="formError" role="alert" class="field-error">{{ formError }}</p>
          <p v-if="saved" role="status" class="ok">Alterações guardadas.</p>
          <button type="submit" :disabled="saving">{{ saving ? 'A guardar…' : 'Guardar' }}</button>
        </form>
      </template>
    </AsyncState>
  </section>
</template>

<style scoped>
.specs {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.25rem 1rem;
}
.specs dt {
  color: #555;
}
.specs dd {
  margin: 0;
}
.price {
  font-weight: 700;
}
.warn {
  color: #b00020;
}
.buy {
  display: inline-block;
  margin: 0.5rem 0 1rem;
  font-weight: 600;
}
.panel {
  display: grid;
  gap: 0.5rem;
  max-width: 22rem;
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.panel h2 {
  margin: 0;
  font-size: 1.1rem;
}
.panel label {
  display: grid;
  gap: 0.25rem;
}
.panel .check {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.field-error {
  margin: 0;
  color: #b00020;
  font-size: 0.9rem;
}
.ok {
  margin: 0;
  color: #2c7a5b;
}
</style>
