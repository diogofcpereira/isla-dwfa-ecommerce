<!-- views/OrdersView.vue — PROVISÓRIO (Passo 2.3): a versão a sério chega no Passo 2.4. -->
<script setup lang="ts">
import { useAuth } from '@/stores/auth'

const auth = useAuth()
</script>

<template>
  <section>
    <h1>As minhas encomendas</h1>
    <p>Olá, {{ auth.user?.username }}. A lista chega no Passo 2.4.</p>
  </section>
</template>
