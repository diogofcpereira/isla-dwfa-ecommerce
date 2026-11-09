// src/router/index.ts — o urls.py do frontend: um URL por ecrã, e o guard.
import { createRouter, createWebHistory } from 'vue-router'

import { useAuth } from '@/stores/auth'
import ProductsView from '@/views/ProductsView.vue'

// Os nossos dados em cada rota, tipados: `requiresAuth: 'yes'` não compila.
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: { name: 'products' } },
    { path: '/products', name: 'products', component: ProductsView },
    {
      // (\d+): só números, como <int:pk> no Django. /products/abc cai no catch-all.
      path: '/products/:id(\\d+)',
      name: 'product',
      props: true, // o :id chega ao componente como a prop `id` (string)
      component: () => import('@/views/ProductView.vue'), // lazy: um chunk só para o detalhe
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
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

// ≈ @login_required com ?next=. Corre antes de cada navegação.
// Protege o ECRÃ; os DADOS protege-os a API (401/403/404 da Ficha 03).
router.beforeEach((to) => {
  const auth = useAuth()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { next: to.fullPath } }
  }
})

export default router
