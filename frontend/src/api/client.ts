// src/api/client.ts — o cliente da API, gerado a partir do schema.yaml (openapi-fetch).
// O compilador conhece todos os URLs, parâmetros e corpos: um URL ou um campo errado é um
// erro de compilação, não um 404 no browser.
import createClient from 'openapi-fetch'

import type { Problem } from '@/types'

import type { paths } from './schema'

// Em desenvolvimento a SPA (5173) fala com a API (8000) noutra origem: CORS.
// No build de produção VITE_API_URL é "" e os pedidos são relativos (/api/v1/...):
// o Nginx serve a SPA e a API na mesma origem.
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = createClient<paths>({
  baseUrl: API_URL,
  headers: { Accept: 'application/json' },
  // Lê o globalThis.fetch em cada pedido (e não só ao criar o cliente):
  // é o que deixa os testes substituírem o fetch com vi.stubGlobal.
  fetch: (request) => globalThis.fetch(request),
})

/** Uma mensagem de erro do DRF em texto: "x", ["x", "y"] ou {"non_field_errors": [...]}. */
function asText(raw: unknown): string | null {
  if (raw === undefined || raw === null) return null
  if (typeof raw === 'string') return raw
  if (Array.isArray(raw)) {
    const parts = raw.filter((x): x is string => typeof x === 'string')
    return parts.length ? parts.join(' ') : null
  }
  if (typeof raw === 'object' && 'non_field_errors' in raw) {
    return asText((raw as { non_field_errors: unknown }).non_field_errors)
  }
  return null
}

export class ApiError extends Error {
  readonly status: number
  readonly problem: Problem | null

  constructor(status: number, problem: Problem | null) {
    const text = problem?.detail ?? problem?.title ?? 'Erro da API'
    super(`${text} (HTTP ${status})`)
    this.name = 'ApiError'
    this.status = status
    this.problem = problem
  }

  /** A mensagem de um campo num 400, ex.: field('price') → "O preço tem de ser positivo." */
  field(name: string): string | null {
    const p = this.problem
    if (!p) return null
    // Problem Details põe os erros em `errors`; o DRF por omissão põe-nos na raiz.
    return asText(p.errors?.[name] ?? p[name])
  }

  /**
   * Os erros de uma lista de linhas, por índice: lines('items')[1]?.car → "Esta viatura já
   * não está à venda.". O DRF manda-os como lista ([{}, {...}]) ou como objeto ({"1": {...}}).
   */
  lines(name: string): Record<number, Record<string, string>> {
    const raw = this.problem?.errors?.[name]
    const out: Record<number, Record<string, string>> = {}
    if (raw === null || typeof raw !== 'object') return out
    const pairs: Array<[string, unknown]> = Array.isArray(raw)
      ? raw.map((value, i): [string, unknown] => [String(i), value])
      : Object.entries(raw)
    for (const [key, value] of pairs) {
      const index = Number(key)
      if (!Number.isInteger(index) || value === null || typeof value !== 'object') continue
      if (Array.isArray(value)) continue // uma lista de textos é um erro da lista, não de uma linha
      const fields: Record<string, string> = {}
      for (const [field, message] of Object.entries(value)) {
        const text = asText(message)
        if (text) fields[field] = text
      }
      out[index] = fields
    }
    return out
  }

  /** A mensagem geral (401, 403, 404, 409…), sem o "(HTTP xxx)". */
  get detail(): string {
    return this.field('non_field_errors') ?? this.problem?.detail ?? this.message
  }
}

type Result<T> = { data?: T; error?: unknown; response: Response }

/**
 * O openapi-fetch nunca lança: devolve { data, error, response }. O resto da app
 * (useFetch, as stores) quer uma promise que LANÇA num erro — este adaptador, escrito uma vez.
 */
export async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await call
  if (!response.ok || data === undefined) {
    // Um 502 do Nginx (API parada) traz HTML, não JSON: aí não há Problem para ler.
    const problem = error !== null && typeof error === 'object' ? (error as Problem) : null
    throw new ApiError(response.status, problem)
  }
  return data
}

/** Para os catch: a mensagem de um erro qualquer (da API ou da rede). */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    // 502/503/504: o Nginx respondeu mas a API não (parada, a arrancar, sem base de dados).
    if (e.status >= 500 && !e.problem?.detail) {
      return `A API não está a responder (HTTP ${e.status}). Tenta outra vez daqui a pouco.`
    }
    return e.detail
  }
  return 'Sem ligação à API. Confirma que está a correr e tenta outra vez.'
}
