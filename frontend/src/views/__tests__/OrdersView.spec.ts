// src/views/__tests__/OrdersView.spec.ts — pagar envia o método; um 409 mostra a mensagem da API.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Order } from '@/types'
import OrdersView from '@/views/OrdersView.vue'

const pending: Order = {
  id: 28,
  customer: 1,
  status: 'pending',
  created_at: '2026-11-20T10:00:00Z',
  items: [{ id: 39, car: 3, car_name: 'Volkswagen Polo', quantity: 1, unit_price: '24900.00' }],
  total: '24900.00',
}

async function mountOrders(url = '/orders') {
  loginAs('ana')
  const router = testRouter([{ path: '/orders', name: 'orders', component: OrdersView }])
  await router.push(url)
  const wrapper = mount(OrdersView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('OrdersView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('o filtro de estado do URL vai para o pedido; pagar envia o método escolhido', async () => {
    const fetch = stubFetch(json(page([pending])), json({ ...pending, status: 'paid' }))
    const wrapper = await mountOrders('/orders?status=pending')

    expect(new URL(requestAt(fetch, 0).url).searchParams.get('status')).toBe('pending')
    const pay = wrapper.findAll('button').find((b) => b.text() === 'Pagar')!
    expect(pay.attributes('disabled')).toBeDefined() // sem método escolhido não paga

    await wrapper.find('select[name="method-28"]').setValue('mbway')
    await pay.trigger('click')
    await flushPromises()

    const post = requestAt(fetch, 1)
    expect(new URL(post.url).pathname).toBe('/api/v1/orders/28/pay/')
    expect(await post.json()).toEqual({ method: 'mbway' })
    expect(wrapper.text()).toContain('Paga')
    expect(wrapper.find('[role="status"]').text()).toContain('Encomenda #28 paga')
  })

  it('um 409 (já paga noutra janela) mostra a mensagem da API na linha', async () => {
    stubFetch(
      json(page([pending])),
      json(
        {
          type: 'about:blank',
          title: 'Conflict',
          status: 409,
          detail: "A encomenda está 'Paga' e não pode ser paga.",
        },
        409,
      ),
    )
    const wrapper = await mountOrders()

    await wrapper.find('select[name="method-28"]').setValue('card')
    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Pagar')!
      .trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe(
      "A encomenda está 'Paga' e não pode ser paga.",
    )
  })
})
