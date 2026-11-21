// src/types.ts — nomes curtos para os tipos GERADOS do schema.yaml (src/api/schema.d.ts).
// A fonte de verdade são os serializers do Django: regenerar com `npm run gen:api`.
import type { components } from '@/api/schema'

type Schemas = components['schemas']

export type Category = Schemas['Category']
export type Me = Schemas['Me']
export type OrderItem = Schemas['OrderItem']
export type OrderStatus = Schemas['StatusEnum'] // 'pending' | 'paid' | 'shipped' | 'cancelled'
export type Order = Schemas['Order'] // total: string | null (uma encomenda sem linhas)

/**
 * Product: `stock` e `is_active` saem opcionais (stock?) porque têm default no modelo — o
 * PEDIDO pode omiti-los. Numa resposta vêm sempre, mas não os estreitamos aqui: cada vista
 * que carrega produtos precisaria de um `as`. Quem os usa trata a ausência (stock ?? 0).
 */
export type Product = Schemas['Product']

/**
 * Corpo de erro da API. O DRF, por omissão, envia { "detail": "..." } ou, num 400,
 * { "campo": ["mensagem"] }; com Problem Details (RFC 9457) os erros por campo vêm em
 * `errors`. Tudo opcional para aceitar as duas formas.
 */
export interface Problem {
  type?: string
  title?: string
  status?: number
  detail?: string
  instance?: string
  errors?: Record<string, unknown>
  [key: string]: unknown
}

/** Os estados de um ecrã que carrega dados. */
export type Status = 'idle' | 'loading' | 'error' | 'ok'
