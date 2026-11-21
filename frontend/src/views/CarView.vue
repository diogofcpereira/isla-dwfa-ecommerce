<!-- views/CarView.vue — o detalhe de uma viatura (/cars/7). O :id vem do URL. -->
<script setup lang="ts">
import { api, unwrap } from '@/api/client'
import AsyncState from '@/components/AsyncState.vue'
import { useFetch } from '@/composables/useFetch'
import { money } from '@/utils/format'

const props = defineProps<{ id: string }>() // vem do URL (props: true na rota)

// props.id é lido dentro do load(): mudar de /cars/1 para /cars/2 volta a carregar.
const {
  data: car,
  status,
  error,
  reload,
} = useFetch(() =>
  unwrap(api.GET('/api/v1/cars/{id}/', { params: { path: { id: Number(props.id) } } })),
)
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
</style>
