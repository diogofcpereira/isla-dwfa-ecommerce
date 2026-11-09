<!-- views/ProductView.vue — o detalhe. O :id da rota chega como prop (props: true). -->
<script setup lang="ts">
import { computed } from 'vue'

import { api, unwrap } from '@/api/client'
import { useFetch } from '@/composables/useFetch'

const props = defineProps<{ id: string }>()

// {id} no caminho é preenchido por params.path — e tem de ser um número.
const {
  data: product,
  status,
  error,
} = useFetch(() =>
  unwrap(api.GET('/api/v1/products/{id}/', { params: { path: { id: Number(props.id) } } })),
)

// Os campos a mostrar num <dl>, como um objeto: o template percorre-o com v-for.
const details = computed((): Record<string, string> => {
  const p = product.value
  if (!p) return {}
  return {
    SKU: p.sku,
    Categoria: p.category_name,
    Preço: `${p.price} €`,
    Stock: String(p.stock ?? 0),
    Ativo: p.is_active ? 'sim' : 'não',
    'Criado em': new Date(p.created_at).toLocaleString('pt-PT'),
  }
})
</script>

<template>
  <section>
    <RouterLink :to="{ name: 'products' }">‹ Todos os produtos</RouterLink>

    <p v-if="status === 'loading'">A carregar…</p>
    <p v-else-if="status === 'error'" class="error">{{ error }}</p>
    <template v-else-if="product">
      <h1>{{ product.name }}</h1>
      <dl>
        <template v-for="(value, label) in details" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value }}</dd>
        </template>
      </dl>
    </template>
  </section>
</template>

<style scoped>
dl {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 0.25rem 1rem;
}
dt {
  font-weight: 600;
}
dd {
  margin: 0;
}
.error {
  color: #b00020;
}
</style>
