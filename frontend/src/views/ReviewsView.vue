<!-- views/ReviewsView.vue — o ecrã do recurso Review (Filipe), do lado do cliente:
     avaliar uma viatura que comprou e gerir as suas avaliações (editar volta a "pendente").
     As regras são da API: só avalia quem comprou (encomenda paga ou entregue), uma vez por
     viatura, nota de 1 a 5 — os erros dela aparecem ao lado do campo. -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import StatusBadge, { type Tone } from '@/components/StatusBadge.vue'
import { useFetch } from '@/composables/useFetch'
import { useAuth } from '@/stores/auth'
import type { Review, ReviewStatus } from '@/types'
import { dateTime, stars } from '@/utils/format'

type Field = 'car' | 'rating' | 'comment'

const TONE: Record<ReviewStatus, Tone> = { pending: 'info', approved: 'ok', hidden: 'bad' }

const auth = useAuth()

// Tudo o que o ecrã precisa, num só load(): o meu perfil, as minhas avaliações e as
// viaturas que comprei (encomendas pagas e entregues).
const { data, status, error, reload } = useFetch(async () => {
  const customers = await unwrap(api.GET('/api/v1/customers/'))
  const me = customers.results.find((c) => c.username === auth.user?.username)
  if (!me) return { me: null, reviews: [] as Review[], bought: [] as Array<[number, string]> }
  const [reviews, paid, delivered] = await Promise.all([
    unwrap(api.GET('/api/v1/reviews/', { params: { query: { customer: me.id } } })),
    unwrap(api.GET('/api/v1/orders/', { params: { query: { status: 'paid' } } })),
    unwrap(api.GET('/api/v1/orders/', { params: { query: { status: 'delivered' } } })),
  ])
  const cars = new Map<number, string>()
  for (const order of [...paid.results, ...delivered.results]) {
    for (const line of order.items) cars.set(line.car, line.car_name)
  }
  return { me, reviews: reviews.results, bought: [...cars.entries()] }
})

const reviews = computed(() => data.value?.reviews ?? [])
// Só as viaturas compradas que ainda não avaliei.
const toReview = computed(() =>
  (data.value?.bought ?? []).filter(([id]) => !reviews.value.some((r) => r.car === id)),
)

// ---- avaliar ----
const form = reactive({ car: null as number | null, rating: 5, comment: '' })
const errors = reactive<Record<Field, string | null>>({ car: null, rating: null, comment: null })
const formError = ref<string | null>(null)
const submitting = ref(false)
const notice = ref<string | null>(null)

function readErrors(e: unknown, target: Record<Field, string | null>): string | null {
  if (e instanceof ApiError && e.status === 400) {
    for (const key of Object.keys(target) as Field[]) target[key] = e.field(key)
    return Object.values(target).some(Boolean) ? null : e.detail
  }
  return errorMessage(e)
}

async function create() {
  submitting.value = true
  notice.value = formError.value = errors.car = errors.rating = errors.comment = null
  try {
    await unwrap(
      api.POST('/api/v1/reviews/', {
        body: { car: form.car ?? 0, rating: form.rating, comment: form.comment },
      }),
    )
    notice.value = 'Obrigado! A avaliação fica visível depois de o gestor a aprovar.'
    form.car = null
    form.comment = ''
    await reload()
  } catch (e) {
    formError.value = readErrors(e, errors)
  } finally {
    submitting.value = false
  }
}

// ---- editar e apagar as minhas ----
const editing = ref<number | null>(null)
const draft = reactive({ rating: 5, comment: '' })
const editErrors = reactive<Record<Field, string | null>>({
  car: null,
  rating: null,
  comment: null,
})
const rowError = reactive<Record<number, string | null>>({})

function startEdit(review: Review) {
  editing.value = review.id
  draft.rating = review.rating
  draft.comment = review.comment ?? ''
  editErrors.rating = editErrors.comment = null
}

async function saveEdit(review: Review) {
  rowError[review.id] = null
  try {
    const updated = await unwrap(
      api.PATCH('/api/v1/reviews/{id}/', {
        params: { path: { id: review.id } },
        body: { rating: draft.rating, comment: draft.comment },
      }),
    )
    if (data.value) {
      data.value.reviews = data.value.reviews.map((r) => (r.id === updated.id ? updated : r))
    }
    editing.value = null
  } catch (e) {
    rowError[review.id] = readErrors(e, editErrors)
  }
}

async function remove(review: Review) {
  rowError[review.id] = null
  const { response, error: problem } = await api.DELETE('/api/v1/reviews/{id}/', {
    params: { path: { id: review.id } },
  })
  if (!response.ok) {
    rowError[review.id] = errorMessage(new ApiError(response.status, problem ?? null))
    return
  }
  await reload()
}
</script>

<template>
  <section>
    <h1>As minhas avaliações</h1>

    <p v-if="auth.isGestor" class="hint">
      És gestor: as avaliações dos clientes moderam-se em
      <RouterLink :to="{ name: 'review-moderation' }">Moderação</RouterLink>.
    </p>

    <AsyncState :status="status" :error="error" @retry="reload">
      <form class="card" novalidate @submit.prevent="create">
        <h2>Avaliar uma viatura que compraste</h2>
        <p v-if="toReview.length === 0" class="hint">
          Não há viaturas por avaliar: só se avalia o que se comprou (encomenda paga ou entregue).
        </p>
        <label>
          Viatura
          <select
            v-model="form.car"
            name="car"
            :aria-invalid="errors.car !== null"
            aria-describedby="car-error"
          >
            <option :value="null" disabled>Escolher…</option>
            <option v-for="[id, name] in toReview" :key="id" :value="id">{{ name }}</option>
          </select>
        </label>
        <p v-if="errors.car" id="car-error" class="field-error">{{ errors.car }}</p>

        <label>
          Nota
          <select
            v-model.number="form.rating"
            name="rating"
            :aria-invalid="errors.rating !== null"
            aria-describedby="rating-error"
          >
            <option v-for="n in [5, 4, 3, 2, 1]" :key="n" :value="n">
              {{ stars(n) }} ({{ n }})
            </option>
          </select>
        </label>
        <p v-if="errors.rating" id="rating-error" class="field-error">{{ errors.rating }}</p>

        <label>
          Comentário (opcional)
          <textarea v-model.trim="form.comment" name="comment" rows="3"></textarea>
        </label>
        <p v-if="errors.comment" class="field-error">{{ errors.comment }}</p>

        <p v-if="formError" role="alert" class="field-error">{{ formError }}</p>
        <p v-if="notice" role="status" class="ok">{{ notice }}</p>
        <button type="submit" :disabled="submitting">
          {{ submitting ? 'A enviar…' : 'Enviar avaliação' }}
        </button>
      </form>

      <h2>Enviadas</h2>
      <p v-if="reviews.length === 0" class="hint">Ainda não avaliaste nenhuma viatura.</p>
      <article v-for="r in reviews" :key="r.id" class="card">
        <header>
          <strong>{{ r.car_name }}</strong>
          <span :aria-label="`${r.rating} em 5`">{{ stars(r.rating) }}</span>
          <StatusBadge :label="r.status_display" :tone="TONE[r.status]" />
          <span class="muted">{{ dateTime(r.created_at) }}</span>
        </header>

        <template v-if="editing === r.id">
          <label>
            Nota
            <select v-model.number="draft.rating" name="edit-rating">
              <option v-for="n in [5, 4, 3, 2, 1]" :key="n" :value="n">{{ n }}</option>
            </select>
          </label>
          <p v-if="editErrors.rating" class="field-error">{{ editErrors.rating }}</p>
          <label>
            Comentário
            <textarea v-model.trim="draft.comment" name="edit-comment" rows="2"></textarea>
          </label>
          <p class="hint">Ao guardar, a avaliação volta a ficar pendente de moderação.</p>
          <div class="actions">
            <button type="button" @click="saveEdit(r)">Guardar</button>
            <button type="button" @click="editing = null">Cancelar</button>
          </div>
        </template>
        <template v-else>
          <p>{{ r.comment || '(sem comentário)' }}</p>
          <div class="actions">
            <button type="button" @click="startEdit(r)">Editar</button>
            <button type="button" @click="remove(r)">Apagar</button>
          </div>
        </template>
        <p v-if="rowError[r.id]" role="alert" class="field-error">{{ rowError[r.id] }}</p>
      </article>
    </AsyncState>
  </section>
</template>

<style scoped>
.card {
  display: grid;
  gap: 0.5rem;
  max-width: 36rem;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.card h2 {
  margin: 0;
  font-size: 1.1rem;
}
.card header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
label {
  display: grid;
  gap: 0.25rem;
}
.actions {
  display: flex;
  gap: 0.5rem;
}
.hint,
.muted {
  color: #666;
  font-size: 0.9rem;
}
.ok {
  margin: 0;
  color: #2c7a5b;
}
.field-error {
  margin: 0;
  color: #b00020;
  font-size: 0.9rem;
}
</style>
