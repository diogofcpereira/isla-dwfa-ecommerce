// src/stores/__tests__/auth.spec.ts — a store, sem rede: o fetch é substituído por vi.fn().
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { authMiddleware } from '@/api/auth'
import { ApiError, api } from '@/api/client'
import { useAuth } from '@/stores/auth'

// Uma resposta JSON falsa, como a API a daria.
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('store auth', () => {
  beforeAll(() => {
    api.use(authMiddleware) // como no main.ts: confirma que o logout não leva Bearer
  })
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia()) // uma store nova em cada teste
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('login() guarda o access em memória, o refresh no localStorage e carrega o user', async () => {
    const fetch = vi
      .fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(json({ access: 'A1', refresh: 'R1' })) // POST /auth/token/
      .mockResolvedValueOnce(json({ id: 1, username: 'ana', groups: [] })) // GET /me/
    vi.stubGlobal('fetch', fetch)

    const auth = useAuth()
    await auth.login('ana', 'pass1234')

    expect(auth.access).toBe('A1')
    expect(auth.user?.username).toBe('ana')
    expect(auth.isLoggedIn).toBe(true)
    expect(localStorage.getItem('refresh')).toBe('R1')
    expect(localStorage.getItem('access')).toBeNull() // o access nunca toca no storage
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('um 401 no login lança ApiError e deixa a store vazia', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof globalThis.fetch>()
        .mockResolvedValueOnce(
          json({ detail: 'No active account found with the given credentials' }, 401),
        ),
    )

    const auth = useAuth()
    await expect(auth.login('ana', 'errada')).rejects.toBeInstanceOf(ApiError)

    expect(auth.isLoggedIn).toBe(false)
    expect(auth.access).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })

  it('logout() limpa a sessão e põe o refresh na blacklist da API', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValueOnce(json({}))
    vi.stubGlobal('fetch', fetch)
    localStorage.setItem('refresh', 'R0')
    const auth = useAuth()
    auth.access = 'A0'

    auth.logout()

    // O ecrã reage logo: a sessão local acaba antes de a API responder.
    expect(auth.access).toBeNull()
    expect(auth.refresh).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
    await flushPromises()
    const request = fetch.mock.calls[0]?.[0] as Request
    expect(new URL(request.url).pathname).toBe('/api/v1/auth/logout/')
    expect(request.headers.get('Authorization')).toBeNull() // o logout não leva Bearer
    expect(await request.json()).toEqual({ refresh: 'R0' })
  })

  it('logout() sem rede não rebenta: a sessão local acaba na mesma', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof globalThis.fetch>().mockRejectedValueOnce(new TypeError('Failed to fetch')),
    )
    localStorage.setItem('refresh', 'R0')
    const auth = useAuth()

    auth.logout()
    await flushPromises()

    expect(auth.isLoggedIn).toBe(false)
    expect(localStorage.getItem('refresh')).toBeNull()
  })
})
