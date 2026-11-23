<!-- views/TestDrivesView.vue — o ecrã do recurso TestDrive (Rúben).
     Cliente: marca um test drive (viatura + dia + hora certa) e cancela os seus.
     Gestor: vê todos, confirma ou recusa os pedidos, e pesquisa por viatura ou cliente.
     A pesquisa, o estado e a página vivem no URL (?search=golf&status=requested&page=2) —
     a pesquisa é a correção do M1 (search_fields no TestDriveViewSet). -->
<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError, api, errorMessage, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import StatusBadge, { type Tone } from '@/components/StatusBadge.vue'
import { useFetch } from '@/composables/useFetch'
import { useAuth } from '@/stores/auth'
import type { Car, TestDrive, TestDriveStatus } from '@/types'
import { dateTime, localToIso } from '@/utils/format'

type Field = 'car' | 'scheduled_for' | 'notes'
type Action = 'confirm' | 'decline' | 'cancel'

const PAGE_SIZE = 20
const HOURS = [9, 10, 11, 12, 14, 15, 16, 17, 18] // a API só aceita horas certas (hh:00)

const LABEL: Record<TestDriveStatus, string> = {
  requested: 'Pedido',
  confirmed: 'Confirmado',
  declined: 'Recusado',
  cancelled: 'Cancelado',
}
const TONE: Record<TestDriveStatus, Tone> = {
  requested: 'info',
  confirmed: 'ok',
  declined: 'bad',
  cancelled: 'neutral',
}

const auth = useAuth()
const route = useRoute()
const router = useRouter()

// ---- o URL é a fonte de verdade ----
function setQuery(change: Record<string, string | undefined>) {
  void router.push({ query: { ...route.query, ...change } })
}
function isStatus(value: unknown): value is TestDriveStatus {
  return typeof value === 'string' && value in LABEL
}
const search = computed({
  get: () => (typeof route.query.search === 'string' ? route.query.search : ''),
  set: (value: string) => setQuery({ search: value || undefined, page: undefined }),
})
const statusFilter = computed({
  get: (): TestDriveStatus | '' => (isStatus(route.query.status) ? route.query.status : ''),
  set: (value: TestDriveStatus | '') => setQuery({ status: value || undefined, page: undefined }),
})
const page = computed(() => {
  const n = Number(route.query.page)
  return Number.isInteger(n) && n > 0 ? n : 1
})

const { data, status, error, reload } = useFetch(() =>
  unwrap(
    api.GET('/api/v1/test-drives/', {
      params: {
        query: {
          search: search.value || undefined,
          status: statusFilter.value || undefined,
          page: page.value,
        },
      },
    }),
  ),
)
const drives = computed(() => data.value?.results ?? [])
const pages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / PAGE_SIZE)))

// ---- marcar (cliente) ----
const cars = ref<Car[]>([])
async function loadCars() {
  try {
    const result = await unwrap(
      api.GET('/api/v1/cars/', { params: { query: { is_active: true } } }),
    )
    cars.value = result.results
  } catch {
    cars.value = [] // o formulário mostra "sem viaturas"; a lista continua a funcionar
  }
}
if (!auth.isGestor) void loadCars()

const form = reactive({ car: null as number | null, day: '', hour: 10, notes: '' })
const errors = reactive<Record<Field, string | null>>({
  car: null,
  scheduled_for: null,
  notes: null,
})
const formError = ref<string | null>(null)
const notice = ref<string | null>(null)
const submitting = ref(false)

function scheduledFor(): string {
  if (!form.day) return ''
  return localToIso(`${form.day}T${String(form.hour).padStart(2, '0')}:00`)
}

async function book() {
  submitting.value = true
  notice.value = formError.value = null
  for (const key of Object.keys(errors) as Field[]) errors[key] = null
  try {
    const created = await unwrap(
      api.POST('/api/v1/test-drives/', {
        body: { car: form.car ?? 0, scheduled_for: scheduledFor(), notes: form.notes },
      }),
    )
    notice.value = `Pedido enviado: ${created.car_name}, ${dateTime(created.scheduled_for)}.`
    form.notes = ''
    await reload()
  } catch (e) {
    if (e instanceof ApiError && e.status === 400) {
      for (const key of Object.keys(errors) as Field[]) errors[key] = e.field(key)
      if (!Object.values(errors).some(Boolean)) formError.value = e.detail
    } else {
      formError.value = errorMessage(e) // 409: outro cliente marcou o mesmo horário agora
    }
  } finally {
    submitting.value = false
  }
}

// ---- mudar de estado ----
const busy = ref<number | null>(null)
const rowError = reactive<Record<number, string | null>>({})

async function act(drive: TestDrive, action: Action) {
  busy.value = drive.id
  rowError[drive.id] = null
  const params = { params: { path: { id: drive.id } } }
  try {
    const updated = await unwrap(
      action === 'confirm'
        ? api.POST('/api/v1/test-drives/{id}/confirm/', params)
        : action === 'decline'
          ? api.POST('/api/v1/test-drives/{id}/decline/', params)
          : api.POST('/api/v1/test-drives/{id}/cancel/', params),
    )
    if (data.value) {
      data.value.results = data.value.results.map((d) => (d.id === updated.id ? updated : d))
    }
  } catch (e) {
    rowError[drive.id] = errorMessage(e) // 409: o estado já não o permite
  } finally {
    busy.value = null
  }
}
</script>

<template>
  <section>
    <h1>{{ auth.isGestor ? 'Test drives' : 'Os meus test drives' }}</h1>

    <form v-if="!auth.isGestor" class="card" novalidate @submit.prevent="book">
      <h2>Marcar um test drive</h2>
      <label>
        Viatura
        <select
          v-model="form.car"
          name="car"
          :aria-invalid="errors.car !== null"
          aria-describedby="car-error"
        >
          <option :value="null" disabled>Escolher…</option>
          <option v-for="car in cars" :key="car.id" :value="car.id">
            {{ car.brand_name }} {{ car.model }} {{ car.version }}
          </option>
        </select>
      </label>
      <p v-if="errors.car" id="car-error" class="field-error">{{ errors.car }}</p>

      <div class="row">
        <label>
          Dia
          <input
            v-model="form.day"
            name="day"
            type="date"
            :aria-invalid="errors.scheduled_for !== null"
            aria-describedby="scheduled-error"
          />
        </label>
        <label>
          Hora
          <select v-model.number="form.hour" name="hour">
            <option v-for="h in HOURS" :key="h" :value="h">{{ h }}:00</option>
          </select>
        </label>
      </div>
      <p v-if="errors.scheduled_for" id="scheduled-error" class="field-error">
        {{ errors.scheduled_for }}
      </p>

      <label>
        Notas (opcional)
        <input v-model.trim="form.notes" name="notes" />
      </label>
      <p v-if="errors.notes" class="field-error">{{ errors.notes }}</p>

      <p v-if="formError" role="alert" class="field-error">{{ formError }}</p>
      <p v-if="notice" role="status" class="ok">{{ notice }}</p>
      <button type="submit" :disabled="submitting">
        {{ submitting ? 'A marcar…' : 'Marcar' }}
      </button>
    </form>

    <form class="filters" role="search" @submit.prevent>
      <label>
        Pesquisar
        <input
          v-model.lazy.trim="search"
          type="search"
          name="search"
          :placeholder="auth.isGestor ? 'Viatura, cliente ou notas' : 'Viatura ou notas'"
        />
      </label>
      <label>
        Estado
        <select v-model="statusFilter" name="status">
          <option value="">Todos</option>
          <option v-for="(label, value) in LABEL" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
    </form>

    <AsyncState
      :status="status"
      :error="error"
      :empty="drives.length === 0"
      :empty-text="
        search || statusFilter
          ? 'Nenhum test drive corresponde à pesquisa.'
          : 'Ainda não há test drives marcados.'
      "
      @retry="reload"
    >
      <article v-for="d in drives" :key="d.id" class="drive">
        <header>
          <strong>{{ d.car_name }}</strong>
          <StatusBadge :label="d.status_display" :tone="TONE[d.status]" />
          <span>{{ dateTime(d.scheduled_for) }}</span>
          <span v-if="auth.isGestor" class="muted">cliente {{ d.customer }}</span>
        </header>
        <p v-if="d.notes" class="muted">{{ d.notes }}</p>
        <div class="actions">
          <template v-if="auth.isGestor && d.status === 'requested'">
            <button type="button" :disabled="busy === d.id" @click="act(d, 'confirm')">
              Confirmar
            </button>
            <button type="button" :disabled="busy === d.id" @click="act(d, 'decline')">
              Recusar
            </button>
          </template>
          <button
            v-if="!auth.isGestor && (d.status === 'requested' || d.status === 'confirmed')"
            type="button"
            :disabled="busy === d.id"
            @click="act(d, 'cancel')"
          >
            Cancelar
          </button>
        </div>
        <p v-if="rowError[d.id]" role="alert" class="field-error">{{ rowError[d.id] }}</p>
      </article>

      <nav v-if="pages > 1" class="pager" aria-label="Páginas">
        <button
          type="button"
          :disabled="!data?.previous"
          @click="setQuery({ page: page > 2 ? String(page - 1) : undefined })"
        >
          Anterior
        </button>
        <span>Página {{ page }} de {{ pages }}</span>
        <button type="button" :disabled="!data?.next" @click="setQuery({ page: String(page + 1) })">
          Seguinte
        </button>
      </nav>
    </AsyncState>
  </section>
</template>

<style scoped>
.card {
  display: grid;
  gap: 0.5rem;
  max-width: 32rem;
  margin-bottom: 1.5rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.card h2 {
  margin: 0;
  font-size: 1.1rem;
}
label {
  display: grid;
  gap: 0.25rem;
}
.row {
  display: flex;
  gap: 1rem;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}
.filters input {
  min-width: 16rem;
}
.drive {
  margin-bottom: 0.75rem;
  padding: 0.75rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.drive header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
.actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.muted {
  color: #666;
  font-size: 0.9rem;
}
.ok {
  margin: 0;
  color: #2c7a5b;
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
}
</style>
