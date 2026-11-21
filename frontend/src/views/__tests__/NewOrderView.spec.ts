// src/views/__tests__/NewOrderView.spec.ts — um formulário com erros: cada erro ao lado da
// linha e do campo certos; e o sucesso leva para as encomendas.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, problem400, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Car, Order } from '@/types'
import NewOrderView from '@/views/NewOrderView.vue'

const car = (id: number, model: string): Car => ({
  id,
  brand: 1,
  brand_name: 'Volkswagen',
  code: `DN-000${id}`,
  model,
  version: '',
  year: 2025,
  fuel: 'petrol',
  fuel_display: 'Gasolina',
  price: '20000.00',
  stock: 3,
  is_active: true,
  created_at: '2026-11-20T10:00:00Z',
})

async function mountForm(url = '/orders/new') {
  loginAs('ana')
  const router = testRouter([{ path: '/orders/new', name: 'new-order', component: NewOrderView }])
  await router.push(url)
  const wrapper = mount(NewOrderView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('NewOrderView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('um 400 mostra cada erro na linha e no campo certos', async () => {
    const fetch = stubFetch(
      json(page([car(1, 'Golf'), car(2, 'Polo')])),
      problem400({ items: { '1': { quantity: ['Só há 3 em stock.'] } } }),
    )
    const { wrapper } = await mountForm('/orders/new?car=1') // a linha 1 já vem com o Golf

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Adicionar linha'))!
      .trigger('click')
    await wrapper.find('select[name="car-1"]').setValue(2)
    await wrapper.find('input[name="quantity-1"]').setValue(9)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(await requestAt(fetch, 1).json()).toEqual({
      items: [
        { car: 1, quantity: 1 },
        { car: 2, quantity: 9 },
      ],
    })
    const lines = wrapper.findAll('fieldset')
    expect(lines[0]!.find('.field-error').exists()).toBe(false)
    expect(lines[1]!.find('.field-error').text()).toBe('Só há 3 em stock.')
    expect(wrapper.find('input[name="quantity-1"]').attributes('aria-invalid')).toBe('true')
  })

  it('um erro da lista inteira (viatura repetida) aparece por cima do botão', async () => {
    stubFetch(
      json(page([car(1, 'Golf')])),
      problem400({ items: ['A mesma viatura aparece em duas linhas: junta-as.'] }),
    )
    const { wrapper } = await mountForm('/orders/new?car=1')

    await wrapper
      .findAll('button')
      .find((b) => b.text().includes('Adicionar linha'))!
      .trigger('click')
    await wrapper.find('select[name="car-1"]').setValue(1)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe(
      'A mesma viatura aparece em duas linhas: junta-as.',
    )
  })

  it('com sucesso vai para /orders com a encomenda nova', async () => {
    const created: Order = {
      id: 31,
      customer: 1,
      status: 'pending',
      created_at: '2026-11-20T10:00:00Z',
      items: [{ id: 50, car: 1, car_name: 'Volkswagen Golf', quantity: 1, unit_price: '20000.00' }],
      total: '20000.00',
    }
    stubFetch(json(page([car(1, 'Golf')])), json(created, 201))
    const { wrapper, router } = await mountForm('/orders/new?car=1')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('orders')
    expect(router.currentRoute.value.query).toEqual({ status: 'pending', created: '31' })
  })
})
