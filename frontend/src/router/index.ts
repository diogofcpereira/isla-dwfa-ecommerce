// src/router/index.ts — o urls.py do frontend: um URL por ecrã, e o guard.
import { createRouter, createWebHistory, type RouteLocationNormalized } from 'vue-router'

import { useAuth } from '@/stores/auth'
import CarsView from '@/views/CarsView.vue'

// Os nossos dados em cada rota, tipados: `requiresAuth: 'yes'` não compila.
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean // ≈ @login_required
    requiresGestor?: boolean // ≈ @user_passes_test(is_gestor); implica requiresAuth
    title?: string // o título do separador do browser (extra do M2)
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: { name: 'cars' } },
    { path: '/cars', name: 'cars', component: CarsView, meta: { title: 'Viaturas' } },
    {
      // (\d+): só números, como <int:pk> no Django. /cars/abc cai no catch-all.
      path: '/cars/:id(\\d+)',
      name: 'car',
      props: true, // o :id chega ao componente como a prop `id` (string)
      component: () => import('@/views/CarView.vue'), // lazy: um chunk só para o detalhe
      meta: { title: 'Viatura' },
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Entrar' },
    },
    {
      path: '/orders',
      name: 'orders',
      component: () => import('@/views/OrdersView.vue'),
      meta: { title: 'Encomendas', requiresAuth: true },
    },
    {
      path: '/orders/new',
      name: 'new-order',
      component: () => import('@/views/NewOrderView.vue'),
      meta: { title: 'Nova encomenda', requiresAuth: true },
    },
    {
      path: '/deliveries',
      name: 'deliveries',
      component: () => import('@/views/DeliveriesView.vue'),
      meta: { title: 'Entregas', requiresAuth: true },
    },
    {
      path: '/deliveries/new',
      name: 'new-delivery',
      component: () => import('@/views/NewDeliveryView.vue'),
      // Só gestores: um cliente que escreva o URL à mão vai para /forbidden.
      meta: { title: 'Agendar entrega', requiresGestor: true },
    },
    {
      path: '/reviews',
      name: 'reviews',
      component: () => import('@/views/ReviewsView.vue'),
      meta: { title: 'Avaliações', requiresAuth: true },
    },
    {
      path: '/reviews/moderation',
      name: 'review-moderation',
      component: () => import('@/views/ReviewModerationView.vue'),
      meta: { title: 'Moderação', requiresGestor: true },
    },
    {
      path: '/test-drives',
      name: 'test-drives',
      component: () => import('@/views/TestDrivesView.vue'),
      meta: { title: 'Test drives', requiresAuth: true },
    },
    {
      path: '/forbidden',
      name: 'forbidden',
      component: () => import('@/views/ForbiddenView.vue'),
      meta: { title: 'Sem permissão' },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: 'Página não encontrada' },
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

// Extra do M2: cada ecrã com o seu título no separador (e no histórico do browser).
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · DriveNow` : 'DriveNow'
})

export default router
