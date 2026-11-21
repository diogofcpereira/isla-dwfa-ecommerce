<!-- views/CarsView.vue — o catálogo público: pesquisa, filtro por combustível e paginação.
     A pesquisa, o combustível e a página vivem no URL (?search=golf&fuel=hybrid&page=2):
     um F5, o botão "voltar" ou um link partilhado mostram exatamente a mesma lista. -->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import CarCard from '@/components/CarCard.vue'
import { useFetch } from '@/composables/useFetch'
import type { Fuel } from '@/types'

const PAGE_SIZE = 20 // igual ao PAGE_SIZE do DRF (config/settings/base.py)

// Record<Fuel, string>: se a API ganhar um combustível novo, isto deixa de compilar.
const FUELS: Record<Fuel, string> = {
  petrol: 'Gasolina',
  diesel: 'Gasóleo',
  hybrid: 'Híbrido',
  electric: 'Elétrico',
}

const route = useRoute()
const router = useRouter()

function isFuel(value: unknown): value is Fuel {
  return typeof value === 'string' && value in FUELS
}

// O URL é a fonte de verdade: os campos leem-no e escrevem nele.
const search = computed({
  get: () => (typeof route.query.search === 'string' ? route.query.search : ''),
  // Uma pesquisa nova volta à página 1 (a página 3 de outra pesquisa pode nem existir).
  set: (value: string) => setQuery({ search: value || undefined, page: undefined }),
})
const fuel = computed({
  get: (): Fuel | '' => (isFuel(route.query.fuel) ? route.query.fuel : ''),
  set: (value: Fuel | '') => setQuery({ fuel: value || undefined, page: undefined }),
})
const page = computed(() => {
  const n = Number(route.query.page)
  return Number.isInteger(n) && n > 0 ? n : 1
})

function setQuery(change: Record<string, string | undefined>) {
  void router.push({ query: { ...route.query, ...change } })
}

function goTo(n: number) {
  setQuery({ page: n > 1 ? String(n) : undefined })
}

const { data, status, error, reload } = useFetch(() =>
  unwrap(
    api.GET('/api/v1/cars/', {
      params: {
        query: {
          search: search.value || undefined,
          fuel: fuel.value || undefined,
          page: page.value,
        },
      },
    }),
  ),
)

const cars = computed(() => data.value?.results ?? [])
const pages = computed(() => Math.max(1, Math.ceil((data.value?.count ?? 0) / PAGE_SIZE)))
</script>

<template>
  <section>
    <h1>Viaturas</h1>

    <form class="filters" role="search" @submit.prevent>
      <label>
        Pesquisar
        <!-- .lazy: só pesquisa ao sair do campo ou com Enter, não a cada tecla -->
        <input
          v-model.lazy.trim="search"
          type="search"
          name="search"
          placeholder="Marca, modelo, versão ou código"
        />
      </label>
      <label>
        Combustível
        <select v-model="fuel" name="fuel">
          <option value="">Todos</option>
          <option v-for="(label, value) in FUELS" :key="value" :value="value">{{ label }}</option>
        </select>
      </label>
    </form>

    <AsyncState
      :status="status"
      :error="error"
      :empty="cars.length === 0"
      empty-text="Nenhuma viatura corresponde à pesquisa."
      @retry="reload"
    >
      <p class="count">{{ data?.count }} viaturas</p>
      <div class="grid">
        <CarCard v-for="car in cars" :key="car.id" :car="car" />
      </div>

      <nav v-if="pages > 1" class="pager" aria-label="Páginas">
        <button type="button" :disabled="!data?.previous" @click="goTo(page - 1)">Anterior</button>
        <span>Página {{ page }} de {{ pages }}</span>
        <button type="button" :disabled="!data?.next" @click="goTo(page + 1)">Seguinte</button>
      </nav>
    </AsyncState>
  </section>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}
.filters label {
  display: grid;
  gap: 0.25rem;
}
.filters input {
  min-width: 18rem;
  padding: 0.4rem;
}
.count {
  color: #555;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 1rem;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}
</style>
