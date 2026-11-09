// src/api/client.ts — o cliente da API, gerado a partir do schema.yaml (openapi-fetch).
// O compilador conhece todos os URLs, parâmetros e respostas: um URL ou um parâmetro
// errado é um erro de compilação, não um 404 no browser.
import createClient from 'openapi-fetch'

import type { Problem } from '@/types'

import type { paths } from './schema'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = createClient<paths>({
  baseUrl: API_URL,
  headers: { Accept: 'application/json' },
  // Lê o globalThis.fetch em cada pedido (e não só ao criar o cliente):
  // é o que deixa os testes substituírem o fetch com vi.stubGlobal.
  fetch: (request) => globalThis.fetch(request),
})

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

  /** A mensagem de um campo num 400 do serializer, ex.: field('quantity') → "Só há 12 em stock." */
  field(name: string): string | null {
    const p = this.problem
    if (!p) return null
    // Problem Details põe os erros em `errors`; o DRF por omissão põe-nos na raiz.
    const raw = p.errors?.[name] ?? p[name]
    if (raw === undefined || raw === null) return null
    return Array.isArray(raw) ? raw.join(' ') : String(raw)
  }

  /** A mensagem geral (401, 403, 404, 409…), sem o "(HTTP xxx)". */
  get detail(): string {
    return this.field('detail') ?? this.field('non_field_errors') ?? this.message
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
    throw new ApiError(response.status, (error ?? null) as Problem | null)
  }
  return data
}
