<!-- views/NewDeliveryView.vue — só gestores (meta.requiresGestor): agendar a entrega de uma
     encomenda paga. Os erros da API (encomenda não paga ou já agendada, data no passado,
     morada em falta) aparecem ao lado do campo respetivo. -->
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import { useFetch } from '@/composables/useFetch'
import { localToIso, money } from '@/utils/format'

type Field = 'order' | 'scheduled_for' | 'address' | 'notes'

const router = useRouter()

// As encomendas pagas são as candidatas (uma já agendada é recusada pela API, com mensagem).
const {
  data: orders,
  status,
  error,
  reload,
} = useFetch(() => unwrap(api.GET('/api/v1/orders/', { params: { query: { status: 'paid' } } })))

const form = reactive({ order: null as number | null, scheduled_for: '', address: '', notes: '' })
const errors = reactive<Record<Field, string | null>>({
  order: null,
  scheduled_for: null,
  address: null,
  notes: null,
})
const formError = ref<string | null>(null)
const submitting = ref(false)

async function submit() {
  submitting.value = true
  formError.value = null
  for (const key of Object.keys(errors) as Field[]) errors[key] = null
  try {
    await unwrap(
      api.POST('/api/v1/deliveries/', {
        body: {
          order: form.order ?? 0, // sem escolha → a API devolve o erro no campo "order"
          scheduled_for: form.scheduled_for ? localToIso(form.scheduled_for) : '',
          address: form.address,
          notes: form.notes,
        },
      }),
    )
    await router.push({ name: 'deliveries', query: { status: 'scheduled' } })
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      for (const key of Object.keys(errors) as Field[]) errors[key] = e.field(key)
      if (!Object.values(errors).some(Boolean)) formError.value = e.detail
    } else {
      formError.value = errorMessage(e) // 403: a sessão já não é de um gestor
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'deliveries' }">← Entregas</RouterLink>
    <h1>Agendar entrega</h1>

    <AsyncState
      :status="status"
      :error="error"
      :empty="(orders?.results.length ?? 0) === 0"
      empty-text="Não há encomendas pagas à espera de entrega."
      @retry="reload"
    >
      <form novalidate @submit.prevent="submit">
        <label>
          Encomenda paga
          <select
            v-model="form.order"
            name="order"
            :aria-invalid="errors.order !== null"
            aria-describedby="order-error"
          >
            <option :value="null" disabled>Escolher…</option>
            <option v-for="o in orders?.results" :key="o.id" :value="o.id">
              #{{ o.id }} — cliente {{ o.customer }} — {{ money(o.total) }}
            </option>
          </select>
        </label>
        <p v-if="errors.order" id="order-error" class="field-error">{{ errors.order }}</p>

        <label>
          Data e hora
          <input
            v-model="form.scheduled_for"
            name="scheduled_for"
            type="datetime-local"
            :aria-invalid="errors.scheduled_for !== null"
            aria-describedby="scheduled-error"
          />
        </label>
        <p v-if="errors.scheduled_for" id="scheduled-error" class="field-error">
          {{ errors.scheduled_for }}
        </p>

        <label>
          Morada
          <input
            v-model.trim="form.address"
            name="address"
            autocomplete="street-address"
            :aria-invalid="errors.address !== null"
            aria-describedby="address-error"
          />
        </label>
        <p v-if="errors.address" id="address-error" class="field-error">{{ errors.address }}</p>

        <label>
          Notas (opcional)
          <textarea v-model.trim="form.notes" name="notes" rows="2"></textarea>
        </label>
        <p v-if="errors.notes" class="field-error">{{ errors.notes }}</p>

        <p v-if="formError" role="alert" class="field-error">{{ formError }}</p>
        <button type="submit" :disabled="submitting">
          {{ submitting ? 'A agendar…' : 'Agendar' }}
        </button>
      </form>
    </AsyncState>
  </section>
</template>

<style scoped>
form {
  display: grid;
  gap: 0.5rem;
  max-width: 28rem;
}
label {
  display: grid;
  gap: 0.25rem;
}
input,
select,
textarea {
  padding: 0.4rem;
  font: inherit;
}
.field-error {
  margin: 0;
  color: #b00020;
  font-size: 0.9rem;
}
</style>
