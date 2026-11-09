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
      router.push({ name: 'login', query: { next: route.fullPath } })
    }
  },
)
</script>

<template>
  <header class="topbar">
    <RouterLink :to="{ name: 'products' }" class="brand">Loja DWFA</RouterLink>
    <nav>
      <RouterLink :to="{ name: 'products' }">Produtos</RouterLink>
      <template v-if="auth.isLoggedIn">
        <RouterLink :to="{ name: 'orders' }">As minhas encomendas</RouterLink>
        <span class="who">{{ auth.user?.username }}</span>
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
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #ddd;
}
.brand {
  font-weight: 700;
  text-decoration: none;
  color: inherit;
}
nav {
  display: flex;
  align-items: center;
  gap: 1rem;
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
