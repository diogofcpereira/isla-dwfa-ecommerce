<!-- views/ReviewModerationView.vue — só gestores (meta.requiresGestor): moderar avaliações.
     Aprovar/ocultar: POST /reviews/{id}/moderate/. Corrigir o comentário: PATCH — e, desde a
     correção do M2, o estado mantém-se (só a edição do autor volta a "pendente").
     O filtro de estado vive no URL (?status=pending é o que abre por omissão). -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import StatusBadge, { type Tone } from '@/components/StatusBadge.vue'
import { useFetch } from '@/composables/useFetch'
import type { Review, ReviewStatus } from '@/types'
import { stars } from '@/utils/format'

const LABEL: Record<ReviewStatus, string> = {
  pending: 'Pendentes',
  approved: 'Aprovadas',
  hidden: 'Ocultas',
}
const TONE: Record<ReviewStatus, Tone> = { pending: 'info', approved: 'ok', hidden: 'bad' }

const route = useRoute()
const router = useRouter()

function isStatus(value: unknown): value is ReviewStatus {
  return typeof value === 'string' && value in LABEL
}
const statusFilter = computed({
  get: (): ReviewStatus => (isStatus(route.query.status) ? route.query.status : 'pending'),
  set: (value: ReviewStatus) => void router.push({ query: { ...route.query, status: value } }),
})

const { data, status, error, reload } = useFetch(() =>
  unwrap(api.GET('/api/v1/reviews/', { params: { query: { status: statusFilter.value } } })),
)
const reviews = computed(() => data.value?.results ?? [])

const busy = ref<number | null>(null)
const rowError = reactive<Record<number, string | null>>({})
const editing = ref<number | null>(null)
const draft = ref('')

function replace(updated: Review) {
  if (!data.value) return
  data.value.results = data.value.results.map((r) => (r.id === updated.id ? updated : r))
}

function startEdit(review: Review) {
  editing.value = review.id
  draft.value = review.comment ?? ''
}

async function moderate(review: Review, next: 'approved' | 'hidden') {
  busy.value = review.id
  rowError[review.id] = null
  try {
    replace(
      await unwrap(
        api.POST('/api/v1/reviews/{id}/moderate/', {
          params: { path: { id: review.id } },
          body: { status: next },
        }),
      ),
    )
  } catch (e) {
    rowError[review.id] = errorMessage(e)
  } finally {
    busy.value = null
  }
}

async function saveComment(review: Review) {
  busy.value = review.id
  rowError[review.id] = null
  try {
    replace(
      await unwrap(
        api.PATCH('/api/v1/reviews/{id}/', {
          params: { path: { id: review.id } },
          body: { comment: draft.value },
        }),
      ),
    )
    editing.value = null
  } catch (e) {
    rowError[review.id] =
      e instanceof ApiError && e.status === 400 ? (e.field('comment') ?? e.detail) : errorMessage(e)
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section>
    <h1>Moderação de avaliações</h1>

    <div class="tabs" role="group" aria-label="Estado">
      <button
        v-for="(label, value) in LABEL"
        :key="value"
        type="button"
        :aria-pressed="statusFilter === value"
        @click="statusFilter = value"
      >
        {{ label }}
      </button>
    </div>

    <AsyncState
      :status="status"
      :error="error"
      :empty="reviews.length === 0"
      empty-text="Não há avaliações neste estado."
      @retry="reload"
    >
      <article v-for="r in reviews" :key="r.id" class="card">
        <header>
          <strong>{{ r.car_name }}</strong>
          <span :aria-label="`${r.rating} em 5`">{{ stars(r.rating) }}</span>
          <StatusBadge :label="r.status_display" :tone="TONE[r.status]" />
          <span class="muted">cliente {{ r.customer }}</span>
        </header>

        <template v-if="editing === r.id">
          <label>
            Comentário
            <textarea v-model.trim="draft" name="moderation-comment" rows="2"></textarea>
          </label>
          <div class="actions">
            <button type="button" :disabled="busy === r.id" @click="saveComment(r)">Guardar</button>
            <button type="button" @click="editing = null">Cancelar</button>
          </div>
        </template>
        <template v-else>
          <p>{{ r.comment || '(sem comentário)' }}</p>
          <div class="actions">
            <button
              v-if="r.status !== 'approved'"
              type="button"
              :disabled="busy === r.id"
              @click="moderate(r, 'approved')"
            >
              Aprovar
            </button>
            <button
              v-if="r.status !== 'hidden'"
              type="button"
              :disabled="busy === r.id"
              @click="moderate(r, 'hidden')"
            >
              Ocultar
            </button>
            <button type="button" @click="startEdit(r)">Corrigir comentário</button>
          </div>
        </template>
        <p v-if="rowError[r.id]" role="alert" class="field-error">{{ rowError[r.id] }}</p>
      </article>
    </AsyncState>
  </section>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.tabs button[aria-pressed='true'] {
  font-weight: 700;
}
.card {
  display: grid;
  gap: 0.5rem;
  max-width: 40rem;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
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
.muted {
  color: #666;
  font-size: 0.9rem;
}
.field-error {
  margin: 0;
  color: #b00020;
  font-size: 0.9rem;
}
</style>
