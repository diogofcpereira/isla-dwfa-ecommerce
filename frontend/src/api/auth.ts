// src/api/auth.ts — middleware do openapi-fetch: o token vai em todos os pedidos,
// e um 401 renova o access UMA vez e repete o pedido.
import type { Middleware } from 'openapi-fetch'

import { useAuth } from '@/stores/auth'

// O login e a renovação não levam Bearer nem são repetidos (senão um 401 do refresh
// pedia outro refresh… em loop).
const SKIP = ['/api/v1/auth/token/', '/api/v1/auth/token/refresh/']

// Uma cópia de cada pedido, guardada antes de ser enviado: o corpo de um Request só se
// pode ler uma vez, por isso a repetição precisa da cópia.
const copies = new Map<string, Request>()

export const authMiddleware: Middleware = {
  onRequest({ request, schemaPath, id }) {
    if (SKIP.includes(schemaPath)) return request
    const auth = useAuth()
    if (auth.access) request.headers.set('Authorization', `Bearer ${auth.access}`)
    copies.set(id, request.clone())
    return request
  },

  async onResponse({ response, id }) {
    const retry = copies.get(id)
    copies.delete(id)
    if (response.status !== 401 || !retry) return response

    const access = await useAuth().refreshAccess() // em caso de falha já fez logout()
    if (!access) return response // devolve o 401 original; o App.vue manda para /login

    retry.headers.set('Authorization', `Bearer ${access}`)
    // A repetição é um fetch simples, fora do middleware: um segundo 401 é a sério.
    return globalThis.fetch(retry)
  },

  onError({ id }) {
    copies.delete(id) // erro de rede: não fica lixo no Map
  },
}
