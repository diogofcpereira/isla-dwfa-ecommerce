// src/router/__tests__/guard.spec.ts — o guard: login com ?next= e ecrãs só de gestores.
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import type { RouteLocationNormalized, RouteMeta } from 'vue-router'

import { authGuard } from '@/router'
import { loginAs } from '@/test/helpers'

// Uma rota de destino falsa, só com o que o guard lê.
const to = (fullPath: string, meta: RouteMeta) => ({ fullPath, meta }) as RouteLocationNormalized

describe('authGuard', () => {
  beforeEach(() => {
    setActivePinia(createPinia()) // sem sessão
  })

  it('rota privada sem sessão → /login?next=<para onde ia>', () => {
    expect(authGuard(to('/test-drives?page=2', { requiresAuth: true }))).toEqual({
      name: 'login',
      query: { next: '/test-drives?page=2' },
    })
  })

  it('rota de gestor com um cliente → /forbidden; com o gestor → deixa passar', () => {
    loginAs('ana')
    expect(authGuard(to('/reviews/moderation', { requiresGestor: true }))).toEqual({
      name: 'forbidden',
    })

    loginAs('gestor', ['gestores'])
    expect(authGuard(to('/reviews/moderation', { requiresGestor: true }))).toBe(true)
  })

  it('rota pública deixa passar sem sessão', () => {
    expect(authGuard(to('/cars', {}))).toBe(true)
  })

  it('cada rota tem um título e o separador mostra-o depois de navegar', async () => {
    const { default: router } = await import('@/router')
    const untitled = router
      .getRoutes()
      .filter((route) => route.path !== '/' && !route.meta.title)
      .map((route) => route.path)
    expect(untitled).toEqual([]) // uma rota nova sem título faz este teste falhar
    await router.push('/cars')
    expect(document.title).toBe('Viaturas · DriveNow')
  })
})
