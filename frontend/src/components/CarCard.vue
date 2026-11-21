<!-- components/CarCard.vue — uma viatura na grelha do catálogo. -->
<script setup lang="ts">
import type { Car } from '@/types'
import { money } from '@/utils/format'

defineProps<{ car: Car }>()
</script>

<template>
  <article class="card">
    <RouterLink :to="{ name: 'car', params: { id: car.id } }" class="title">
      {{ car.brand_name }} {{ car.model }}
    </RouterLink>
    <p class="version">{{ car.version }} · {{ car.year }} · {{ car.fuel_display }}</p>
    <p class="price">{{ money(car.price) }}</p>
    <p v-if="car.stock === 0" class="out">Esgotada</p>
  </article>
</template>

<style scoped>
.card {
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fff;
}
.title {
  font-weight: 600;
}
.version {
  margin: 0.25rem 0;
  color: #555;
  font-size: 0.9rem;
}
.price {
  margin: 0;
  font-weight: 700;
}
.out {
  margin: 0.25rem 0 0;
  color: #b00020;
  font-size: 0.85rem;
}
</style>
