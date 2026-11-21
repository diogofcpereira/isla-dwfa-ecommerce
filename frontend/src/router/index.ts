// src/router/index.ts — o urls.py do frontend: um URL por ecrã, e o guard.
import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '@/stores/auth'
import CarsView from '@/views/CarsView.vue'

// Os nossos dados em cada rota, tipados: `requiresAuth: 'yes'` não compila.
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: { name: 'cars' } },
    { path: '/cars', name: 'cars', component: CarsView },
    {
      // (\d+): só números, como <int:pk> no Django. /cars/abc cai no catch-all.
      path: '/cars/:id(\\d+)',
      name: 'car',
      props: true, // o :id chega ao componente como a prop `id` (string)
      component: () => import('@/views/CarView.vue'), // lazy: um chunk só para o detalhe
    },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

// ≈ @login_required com ?next=. Corre antes de cada navegação.
// Protege o ECRÃ; os DADOS protege-os a API (401/403/404 do M1).
router.beforeEach((to) => {
  const auth = useAuth()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { next: to.fullPath } }
  }
})

export default router
