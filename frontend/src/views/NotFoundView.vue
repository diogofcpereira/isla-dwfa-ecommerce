<!-- views/NotFoundView.vue — qualquer URL que nenhuma rota reconhece. -->
<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <section>
    <h1>Página não encontrada</h1>
    <p>
      O endereço <code>{{ route.fullPath }}</code> não corresponde a nenhum ecrã.
    </p>
    <RouterLink :to="{ name: 'products' }">Ir para os produtos</RouterLink>
  </section>
</template>
