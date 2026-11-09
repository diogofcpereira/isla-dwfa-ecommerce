// src/api/__tests__/auth.spec.ts — o middleware: 401 → renovar UMA vez → repetir.
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

import { authMiddleware } from '@/api/auth'
import { api, unwrap } from '@/api/client'
import { useFetch } from '@/composables/useFetch'
import { useAuth } from '@/stores/auth'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const page = { count: 0, next: null, previous: null, results: [] }

describe('authMiddleware', () => {
  beforeAll(() => {
    api.use(authMiddleware)
  })
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('refresh', 'R0')
    setActivePinia(createPinia())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('envia o Bearer; num 401 renova e repete o pedido com o access novo', async () => {
    const fetch = vi
      .fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(json({ detail: 'Token expirado' }, 401)) // GET /orders/
      .mockResolvedValueOnce(json({ access: 'NEW', refresh: 'R1' })) // POST /refresh/
      .mockResolvedValueOnce(json(page)) // GET /orders/ outra vez
    vi.stubGlobal('fetch', fetch)
    const auth = useAuth()
    auth.access = 'OLD'

    const data = await unwrap(api.GET('/api/v1/orders/'))

    expect(data.count).toBe(0)
    expect(fetch).toHaveBeenCalledTimes(3)
    const first = fetch.mock.calls[0]?.[0] as Request
    const retry = fetch.mock.calls[2]?.[0] as Request
    expect(first.headers.get('Authorization')).toBe('Bearer OLD')
    expect(retry.headers.get('Authorization')).toBe('Bearer NEW')
    expect(localStorage.getItem('refresh')).toBe('R1') // rodado
  })

  it('se a renovação falhar: logout, sem segunda tentativa', async () => {
    const fetch = vi
      .fn<typeof globalThis.fetch>()
      .mockResolvedValueOnce(json({ detail: 'Token expirado' }, 401)) // GET /orders/
      .mockResolvedValueOnce(json({ detail: 'Token is blacklisted' }, 401)) // POST /refresh/
    vi.stubGlobal('fetch', fetch)
    const auth = useAuth()
    auth.access = 'OLD'

    await expect(unwrap(api.GET('/api/v1/orders/'))).rejects.toMatchObject({ status: 401 })

    expect(fetch).toHaveBeenCalledTimes(2) // nunca em loop
    expect(auth.access).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })

  it('mudar o token não volta a correr o useFetch (sem pedidos repetidos)', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockImplementation(async () => json(page))
    vi.stubGlobal('fetch', fetch)
    const auth = useAuth()
    auth.access = 'A'

    useFetch(() => unwrap(api.GET('/api/v1/products/')))
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(1)

    auth.access = 'B' // como numa renovação
    auth.logout() // e como ao sair
    await nextTick()
    await flushPromises()
    expect(fetch).toHaveBeenCalledTimes(1) // continua 1
  })
})
