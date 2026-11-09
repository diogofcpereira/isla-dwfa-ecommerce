<!-- views/ProductsView.vue — a lista: pesquisa e página vivem no URL (?search=&page=). -->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api, unwrap } from '@/api/client'
import ProductCard from '@/components/ProductCard.vue'
import { useFetch } from '@/composables/useFetch'

const route = useRoute()
const router = useRouter()

// O URL é a fonte de verdade. Escrever a pesquisa reescreve o URL (e volta à página 1).
const search = computed({
  get: () => String(route.query.search ?? ''),
  set: (value: string) =>
    router.replace({
      query: { ...route.query, search: value || undefined, page: undefined },
    }),
})

const page = computed(() => Number(route.query.page ?? 1))

// O URL e os parâmetros são verificados pelo compilador (paths do schema.d.ts):
// query: { foo: 1 } não compila. O tipo de `data` (PaginatedProductList) é inferido.
const { data, status, error, reload } = useFetch(() =>
  unwrap(
    api.GET('/api/v1/products/', {
      params: {
        query: {
          search: search.value || undefined,
          page: page.value > 1 ? page.value : undefined,
        },
      },
    }),
  ),
)

function goTo(n: number) {
  // push (não replace): o botão Retroceder do browser volta à página anterior.
  router.push({ query: { ...route.query, page: n > 1 ? n : undefined } })
}

function open(id: number) {
  router.push({ name: 'product', params: { id } })
}
</script>

<template>
  <section>
    <h1>Produtos</h1>

    <!-- .lazy: atualiza no "change" (Enter ou sair do campo), não a cada tecla -->
    <input
      v-model.lazy="search"
      type="search"
      class="search"
      placeholder="Pesquisar por nome ou SKU…"
    />

    <p v-if="status === 'loading' && !data">A carregar…</p>
    <p v-else-if="status === 'error'" class="error">
      {{ error }} <button type="button" @click="reload">Tentar outra vez</button>
    </p>
    <template v-else-if="data">
      <p class="summary">
        {{ data.results.length }} de {{ data.count }} produtos · página {{ page }}
        <span v-if="status === 'loading'"> · a atualizar…</span>
      </p>
      <p v-if="data.count === 0">Nenhum produto encontrado.</p>
      <div class="grid">
        <ProductCard v-for="p in data.results" :key="p.id" :product="p" @select="open" />
      </div>
      <nav class="pager">
        <button type="button" :disabled="!data.previous" @click="goTo(page - 1)">‹ Anterior</button>
        <button type="button" :disabled="!data.next" @click="goTo(page + 1)">Seguinte ›</button>
      </nav>
    </template>
  </section>
</template>

<style scoped>
.search {
  width: 100%;
  max-width: 28rem;
  padding: 0.5rem;
  font-size: 1rem;
}
.summary {
  color: #6b6b6b;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 0.75rem;
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
