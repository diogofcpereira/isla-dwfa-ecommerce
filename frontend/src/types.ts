// src/types.ts — nomes curtos para os tipos GERADOS do schema.yaml (src/api/schema.d.ts).
// Nenhum tipo da API é escrito à mão: a fonte de verdade são os serializers do Django.
// Depois de mudar a API: `npm run gen:api` e o type-check aponta o que deixou de bater certo.
import type { components } from '@/api/schema'

type Schemas = components['schemas']

// ---- catálogo ----
export type Brand = Schemas['Brand']
export type Car = Schemas['Car'] // stock? e is_active? saem opcionais: têm default no modelo
export type Fuel = Schemas['FuelEnum'] // 'petrol' | 'diesel' | 'hybrid' | 'electric'
export type CarPatch = Schemas['PatchedCarRequest'] // o corpo de um PATCH /cars/{id}/

// ---- sessão ----
export type Me = Schemas['Me']

// ---- encomendas e pagamento ----
export type Order = Schemas['Order']
export type OrderLine = Schemas['OrderLine']
export type OrderStatus = Schemas['OrderStatusEnum'] // 'pending' | 'paid' | 'delivered' | 'cancelled'
export type PaymentMethod = Schemas['MethodEnum'] // 'transfer' | 'financing' | 'card' | 'mbway'

// ---- recursos do M1 (um por membro) ----
export type Delivery = Schemas['Delivery'] // Diogo
export type DeliveryStatus = Schemas['DeliveryStatusEnum'] // 'scheduled' | 'in_transit' | 'delivered'
export type Review = Schemas['Review'] // Filipe
export type ReviewStatus = Schemas['ReviewStatusEnum'] // 'pending' | 'approved' | 'hidden'

/**
 * Corpo de erro da API: Problem Details (RFC 9457), como o M1 os devolve.
 * `errors` traz os erros por campo de um 400; o resto são membros de extensão (ex.: `code`).
 */
export interface Problem {
  type?: string
  title?: string
  status?: number
  detail?: string
  instance?: string
  code?: string
  errors?: Record<string, unknown>
  [key: string]: unknown
}

/** Os estados de um ecrã que carrega dados (o "empty" decide-se com os dados na mão). */
export type Status = 'idle' | 'loading' | 'error' | 'ok'
