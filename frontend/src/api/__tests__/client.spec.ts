// src/api/__tests__/client.spec.ts — ler os erros da API: por campo, por linha e sem API.
import { describe, expect, it } from 'vitest'

import { ApiError, errorMessage } from '@/api/client'

const problem = (errors: Record<string, unknown>) =>
  new ApiError(400, { status: 400, detail: 'O pedido tem dados inválidos.', errors })

describe('ApiError', () => {
  it('field() lê o erro de um campo em `errors` (Problem Details do M1)', () => {
    const e = problem({ price: ['O preço tem de ser positivo.'], year: ['A.', 'B.'] })
    expect(e.field('price')).toBe('O preço tem de ser positivo.')
    expect(e.field('year')).toBe('A. B.') // várias mensagens juntam-se
    expect(e.field('stock')).toBeNull()
  })

  it('lines() lê os erros por linha e field() o erro da lista inteira', () => {
    const byLine = problem({ items: { '1': { quantity: ['Só há 14 em stock.'] } } })
    expect(byLine.lines('items')).toEqual({ 1: { quantity: 'Só há 14 em stock.' } })
    expect(byLine.field('items')).toBeNull()

    const whole = problem({ items: ['A mesma viatura aparece em duas linhas.'] })
    expect(whole.lines('items')).toEqual({})
    expect(whole.field('items')).toBe('A mesma viatura aparece em duas linhas.')

    const empty = problem({ items: { non_field_errors: ['This list may not be empty.'] } })
    expect(empty.field('items')).toBe('This list may not be empty.')
  })

  it('errorMessage(): 409 com a mensagem da API; 502 sem corpo; sem rede', () => {
    const conflict = new ApiError(409, { status: 409, detail: 'A encomenda já foi paga.' })
    expect(errorMessage(conflict)).toBe('A encomenda já foi paga.')
    expect(errorMessage(new ApiError(502, null))).toBe(
      'A API não está a responder (HTTP 502). Tenta outra vez daqui a pouco.',
    )
    expect(errorMessage(new TypeError('Failed to fetch'))).toContain('Sem ligação à API')
  })
})
