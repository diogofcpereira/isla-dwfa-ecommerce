// src/views/__tests__/ReviewsView.spec.ts — avaliar o que se comprou; os erros da API no campo.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, problem400, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Order, Review } from '@/types'
import ReviewsView from '@/views/ReviewsView.vue'

const me = { id: 7, user: 2, username: 'ana', email: 'ana@example.com', phone: '', address: '' }
const paid: Order = {
  id: 3,
  customer: 7,
  status: 'paid',
  created_at: '2026-11-20T10:00:00Z',
  items: [{ id: 4, car: 13, car_name: 'Toyota Yaris', quantity: 1, unit_price: '21000.00' }],
  total: '21000.00',
}
const mine: Review = {
  id: 9,
  car: 13,
  car_name: 'Toyota Yaris',
  customer: 7,
  rating: 4,
  comment: 'Bom carro.',
  status: 'approved',
  status_display: 'Aprovada',
  created_at: '2026-11-20T10:00:00Z',
}

async function mountReviews(...responses: Response[]) {
  loginAs('ana')
  const fetch = stubFetch(...responses)
  const router = testRouter([{ path: '/reviews', name: 'reviews', component: ReviewsView }])
  await router.push('/reviews')
  const wrapper = mount(ReviewsView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, fetch }
}

describe('ReviewsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('pede só as minhas (?customer=) e oferece as viaturas compradas por avaliar', async () => {
    const { wrapper, fetch } = await mountReviews(
      json(page([me])), // GET /customers/
      json(page([])), // GET /reviews/?customer=7
      json(page([paid])), // GET /orders/?status=paid
      json(page([])), // GET /orders/?status=delivered
    )

    expect(new URL(requestAt(fetch, 1).url).searchParams.get('customer')).toBe('7')
    const options = wrapper.findAll('select[name="car"] option').map((o) => o.text())
    expect(options).toEqual(['Escolher…', 'Toyota Yaris'])
    expect(wrapper.text()).toContain('Ainda não avaliaste nenhuma viatura.')
  })

  it('um 400 da API mostra o erro ao lado da viatura', async () => {
    const { wrapper, fetch } = await mountReviews(
      json(page([me])),
      json(page([])),
      json(page([paid])),
      json(page([])),
      problem400({ car: ['Já avaliaste esta viatura: edita a tua avaliação.'] }),
    )

    await wrapper.find('select[name="car"]').setValue(13)
    await wrapper.find('select[name="rating"]').setValue(3)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(await requestAt(fetch, 4).json()).toEqual({ car: 13, rating: 3, comment: '' })
    expect(wrapper.find('#car-error').text()).toBe(
      'Já avaliaste esta viatura: edita a tua avaliação.',
    )
    expect(wrapper.find('select[name="car"]').attributes('aria-invalid')).toBe('true')
  })

  it('editar a minha avaliação envia um PATCH e mostra-a pendente', async () => {
    const { wrapper, fetch } = await mountReviews(
      json(page([me])),
      json(page([mine])),
      json(page([paid])),
      json(page([])),
      json({ ...mine, rating: 2, status: 'pending', status_display: 'Pendente' }),
    )

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Editar')!
      .trigger('click')
    await wrapper.find('select[name="edit-rating"]').setValue(2)
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Guardar')!
      .trigger('click')
    await flushPromises()

    const patch = requestAt(fetch, 4)
    expect(patch.method).toBe('PATCH')
    expect(new URL(patch.url).pathname).toBe('/api/v1/reviews/9/')
    expect(wrapper.text()).toContain('Pendente')
  })
})
