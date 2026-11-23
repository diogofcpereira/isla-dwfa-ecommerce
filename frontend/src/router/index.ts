// src/router/index.ts — o urls.py do frontend: um URL por ecrã, e o guard.
import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'

import { useAuth } from '@/stores/auth'
import CarsView from '@/views/CarsView.vue'

// Os nossos dados em cada rota, tipados: `requiresAuth: 'yes'` não compila.
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean // ≈ @login_required
    requiresGestor?: boolean // ≈ @user_passes_test(is_gestor); implica requiresAuth
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
      path: '/orders',
      name: 'orders',
      component: () => import('@/views/OrdersView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/orders/new',
      name: 'new-order',
      component: () => import('@/views/NewOrderView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/deliveries',
      name: 'deliveries',
      component: () => import('@/views/DeliveriesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/deliveries/new',
      name: 'new-delivery',
      component: () => import('@/views/NewDeliveryView.vue'),
      meta: { requiresGestor: true }, // só gestores: um cliente vai para /forbidden
    },
    {
      path: '/reviews',
      name: 'reviews',
      component: () => import('@/views/ReviewsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/reviews/moderation',
      name: 'review-moderation',
      component: () => import('@/views/ReviewModerationView.vue'),
      meta: { requiresGestor: true },
    },
    {
      path: '/forbidden',
      name: 'forbidden',
      component: () => import('@/views/ForbiddenView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

/**
 * O guard, exportado para se testar sem browser. Corre antes de cada navegação.
 * Protege o ECRÃ; os DADOS protege-os a API (401/403/404 do M1) — esconder não chega.
 */
export function authGuard(to: RouteLocationNormalized) {
  const auth = useAuth()
  const needsLogin = to.meta.requiresAuth || to.meta.requiresGestor
  if (needsLogin && !auth.isLoggedIn) {
    return { name: 'login', query: { next: to.fullPath } } // depois do login, volta aqui
  }
  if (to.meta.requiresGestor && !auth.isGestor) {
    return { name: 'forbidden' } // autenticado, mas cliente: não é para ele
  }
  return true
}

router.beforeEach(authGuard)

export default router
