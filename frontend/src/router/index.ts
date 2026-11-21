// src/router/index.ts — o urls.py do frontend: um URL por ecrã, e o guard.
import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '@/stores/auth'

// Os nossos dados em cada rota, tipados: `requiresAuth: 'yes'` não compila.
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // O catálogo (/cars) chega no commit seguinte; até lá a raiz leva ao login.
    { path: '/', redirect: { name: 'login' } },
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
