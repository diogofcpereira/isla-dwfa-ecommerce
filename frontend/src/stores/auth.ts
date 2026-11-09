// src/stores/auth.ts — a sessão: quem está autenticado e com que tokens.
// Decisão (Aula 04 / Ficha 03): o access (30 min) só em memória; o refresh (1 dia,
// roda a cada uso e vai para a blacklist) no localStorage, para sobreviver ao F5.
import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import { api, unwrap } from '@/api/client'
import type { Me } from '@/types'

const REFRESH_KEY = 'refresh'

export const useAuth = defineStore('auth', () => {
  // ---- estado ----
  const access = ref<string | null>(null) // só memória: um F5 apaga-o
  const refresh = ref<string | null>(localStorage.getItem(REFRESH_KEY))
  const user = ref<Me | null>(null)
  const ready = ref(false) // o bootstrap já correu?

  // Uma cópia NÃO reativa do access, para o middleware. Se o middleware lesse access.value,
  // o watchEffect do useFetch (que está a correr quando o pedido sai) ficava a depender do
  // token, e cada renovação ou logout repetia os pedidos de todas as listas no ecrã.
  // flush: 'sync' → a cópia muda no mesmo instante que o ref (também nos testes).
  let currentAccess: string | null = null
  watch(access, (value) => (currentAccess = value), { flush: 'sync' })

  // ---- getters ----
  const isLoggedIn = computed(() => user.value !== null)
  const isGestor = computed(() => user.value?.groups.includes('gestores') ?? false)

  // Um só sítio escreve o refresh: o ref e o localStorage nunca discordam.
  function setRefresh(value: string | null) {
    refresh.value = value
    if (value) localStorage.setItem(REFRESH_KEY, value)
    else localStorage.removeItem(REFRESH_KEY)
  }

  /** O access para pôr no cabeçalho, lido sem criar dependências reativas. */
  function accessToken(): string | null {
    return currentAccess
  }

  // ---- ações ----
  async function login(username: string, password: string) {
    const pair = await unwrap(api.POST('/api/v1/auth/token/', { body: { username, password } }))
    access.value = pair.access
    setRefresh(pair.refresh)
    try {
      user.value = await unwrap(api.GET('/api/v1/me/'))
    } catch (e) {
      logout() // sem utilizador não há sessão: não deixar tokens soltos
      throw e
    }
  }

  function logout() {
    access.value = null
    setRefresh(null)
    user.value = null
  }

  // Se dois pedidos receberem 401 ao mesmo tempo, os dois esperam pela MESMA renovação.
  // Duas renovações em paralelo gastariam o mesmo refresh duas vezes — e a segunda falharia,
  // porque a primeira já o pôs na blacklist (ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION).
  let renewing: Promise<string | null> | null = null

  /** Pede um access novo com o refresh guardado. Devolve-o, ou null (e faz logout) se falhar. */
  function refreshAccess(): Promise<string | null> {
    renewing ??= (async () => {
      try {
        // Lido do localStorage e não do ref: outro separador pode já ter rodado o refresh
        // (e o que este separador tem em memória já estaria na blacklist).
        const current = localStorage.getItem(REFRESH_KEY)
        if (!current) {
          logout()
          return null
        }
        const { data } = await api.POST('/api/v1/auth/token/refresh/', {
          body: { refresh: current },
        })
        if (!data) {
          logout() // refresh expirado ou na blacklist: a sessão acabou
          return null
        }
        access.value = data.access
        if (data.refresh) setRefresh(data.refresh) // rodado: o antigo deixou de servir
        return data.access
      } finally {
        renewing = null
      }
    })()
    return renewing
  }

  /** No arranque da app: se há refresh guardado, renova e carrega /me/ — sem login a cada F5. */
  async function bootstrap() {
    try {
      if (refresh.value && (await refreshAccess())) {
        user.value = await unwrap(api.GET('/api/v1/me/'))
      }
    } catch {
      user.value = null // API em baixo: a app arranca sem sessão (o refresh fica guardado)
    } finally {
      ready.value = true
    }
  }

  return {
    access,
    refresh,
    user,
    ready,
    isLoggedIn,
    isGestor,
    login,
    logout,
    refreshAccess,
    bootstrap,
    accessToken,
  }
})
