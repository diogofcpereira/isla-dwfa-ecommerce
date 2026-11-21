// src/stores/__tests__/auth.spec.ts — a store, sem rede: o fetch é substituído por vi.fn().
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { useAuth } from '@/stores/auth'

// Uma resposta JSON falsa, como a API a daria.
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('store auth', () => {
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

  it('logout() limpa o estado e o localStorage', async () => {
    localStorage.setItem('refresh', 'R0')
    const auth = useAuth()
    auth.logout()

    expect(auth.refresh).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })
})
