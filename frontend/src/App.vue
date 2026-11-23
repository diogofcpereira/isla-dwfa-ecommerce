<script setup lang="ts">
import { watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/stores/auth'

const auth = useAuth()
const route = useRoute()
const router = useRouter()

// A sessão acabou (Sair, ou a renovação do token falhou) num ecrã privado → /login.
// O guard só corre quando se navega; isto cobre o caso de já lá estarmos.
watch(
  () => auth.isLoggedIn,
  (loggedIn) => {
    if (!loggedIn && route.meta.requiresAuth) {
      void router.push({ name: 'login', query: { next: route.fullPath } })
    }
  },
)
</script>

<template>
  <header class="topbar">
    <RouterLink :to="{ name: 'cars' }" class="brand">DriveNow</RouterLink>
    <nav aria-label="Principal">
      <RouterLink :to="{ name: 'cars' }">Viaturas</RouterLink>
      <template v-if="auth.isLoggedIn">
        <RouterLink :to="{ name: 'orders' }">Encomendas</RouterLink>
        <RouterLink :to="{ name: 'deliveries' }">Entregas</RouterLink>
        <RouterLink v-if="auth.isGestor" :to="{ name: 'review-moderation' }">Moderação</RouterLink>
        <RouterLink v-else :to="{ name: 'reviews' }">Avaliações</RouterLink>
        <RouterLink :to="{ name: 'test-drives' }">Test drives</RouterLink>
        <span class="who">
          {{ auth.user?.username }}<template v-if="auth.isGestor"> · gestor</template>
        </span>
        <button type="button" @click="auth.logout()">Sair</button>
      </template>
      <RouterLink v-else :to="{ name: 'login' }">Entrar</RouterLink>
    </nav>
  </header>

  <main class="content">
    <RouterView />
  </main>
</template>

<style scoped>
.topbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #ddd;
  background: #fff;
}
.brand {
  font-weight: 700;
  text-decoration: none;
  color: inherit;
}
nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem;
}
nav a.router-link-active {
  font-weight: 600;
}
.who {
  color: #6b6b6b;
}
.content {
  max-width: 64rem;
  margin: 0 auto;
  padding: 1rem 1.5rem 3rem;
}
</style>
