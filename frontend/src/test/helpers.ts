// src/test/helpers.ts — utilitários partilhados pelos testes (não entra no build).
import axe from 'axe-core'
import { createPinia, setActivePinia } from 'pinia'
import { vi } from 'vitest'
import { createMemoryHistory, createRouter, type RouteRecordRaw } from 'vue-router'

import { useAuth } from '@/stores/auth'
import type { Me } from '@/types'

/** Uma resposta JSON falsa, como a API a daria. */
export const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

/** Uma página do DRF com estes resultados. */
export const page = <T>(results: T[], count = results.length) => ({
  count,
  next: null,
  previous: null,
  results,
})

/** Um Problem Details 400 com erros por campo, como o core/exceptions.py do M1 o devolve. */
export const problem400 = (errors: Record<string, unknown>) =>
  json(
    {
      type: 'about:blank',
      title: 'Bad Request',
      status: 400,
      detail: 'O pedido tem dados inválidos.',
      errors,
    },
    400,
  )

/** Substitui o fetch global por um vi.fn com estas respostas, por ordem. */
export function stubFetch(...responses: Response[]) {
  const fetch = vi.fn<typeof globalThis.fetch>()
  for (const r of responses) fetch.mockResolvedValueOnce(r)
  vi.stubGlobal('fetch', fetch)
  return fetch
}

/** O Request que o fetch recebeu na chamada n (0 = a primeira). */
export function requestAt(fetch: ReturnType<typeof stubFetch>, n: number): Request {
  return fetch.mock.calls[n]?.[0] as Request
}

/** Uma store nova, já com sessão (sem passar pelo login). */
export function loginAs(username: string, groups: string[] = []) {
  setActivePinia(createPinia())
  const auth = useAuth()
  auth.access = 'TEST'
  auth.user = { id: 1, username, groups } satisfies Me
  return auth
}

/** Um router em memória com estas rotas e as que os ecrãs usam em RouterLink. */
export function testRouter(routes: RouteRecordRaw[]) {
  const stub = { template: '<p>stub</p>' }
  const names = [
    'cars',
    'car',
    'login',
    'forbidden',
    'orders',
    'new-order',
    'deliveries',
    'new-delivery',
    'reviews',
    'review-moderation',
    'test-drives',
  ]
  const extra = names
    .filter((name) => !routes.some((r) => r.name === name))
    .map((name) => ({ path: `/__${name}/:id?`, name, component: stub }))
  return createRouter({ history: createMemoryHistory(), routes: [...routes, ...extra] })
}

/**
 * Problemas de acessibilidade encontrados pelo axe-core (as regras WCAG 2.x A e AA) num
 * elemento montado no documento. Devolve uma lista legível, para o teste mostrar o que falhou.
 * O contraste de cores não entra: o jsdom não calcula estilos.
 */
export async function a11yViolations(element: Element): Promise<string[]> {
  const result = await axe.run(element, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
    rules: { 'color-contrast': { enabled: false } },
  })
  return result.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.length}×)`)
}
