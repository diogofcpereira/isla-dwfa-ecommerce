// src/views/__tests__/NewDeliveryView.spec.ts — agendar (gestor): erros ao lado dos campos.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, problem400, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Order } from '@/types'
import NewDeliveryView from '@/views/NewDeliveryView.vue'

const paid: Order = {
  id: 12,
  customer: 1,
  status: 'paid',
  created_at: '2026-11-20T10:00:00Z',
  items: [{ id: 1, car: 1, car_name: 'Volkswagen Golf', quantity: 1, unit_price: '32500.00' }],
  total: '32500.00',
}

async function mountForm() {
  loginAs('gestor', ['gestores'])
  const router = testRouter([
    { path: '/deliveries/new', name: 'new-delivery', component: NewDeliveryView },
  ])
  await router.push('/deliveries/new')
  const wrapper = mount(NewDeliveryView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('NewDeliveryView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('um 400 mostra cada erro ao lado do seu campo', async () => {
    const fetch = stubFetch(
      json(page([paid])),
      problem400({
        scheduled_for: ['A data da entrega tem de ser no futuro.'],
        address: ['This field may not be blank.'],
      }),
    )
    const { wrapper } = await mountForm()

    expect(new URL(requestAt(fetch, 0).url).searchParams.get('status')).toBe('paid')
    await wrapper.find('select[name="order"]').setValue(12)
    await wrapper.find('input[name="scheduled_for"]').setValue('2020-01-01T10:00')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const body = await requestAt(fetch, 1).json()
    expect(body.order).toBe(12)
    expect(body.scheduled_for).toBe(new Date('2020-01-01T10:00').toISOString())
    expect(wrapper.find('#scheduled-error').text()).toBe('A data da entrega tem de ser no futuro.')
    expect(wrapper.find('#address-error').text()).toBe('This field may not be blank.')
    expect(wrapper.find('#order-error').exists()).toBe(false)
  })

  it('com sucesso volta às entregas agendadas', async () => {
    stubFetch(json(page([paid])), json({ id: 9 }, 201))
    const { wrapper, router } = await mountForm()

    await wrapper.find('select[name="order"]').setValue(12)
    await wrapper.find('input[name="scheduled_for"]').setValue('2026-12-01T10:00')
    await wrapper.find('input[name="address"]').setValue('Rua das Flores, 10, Porto')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('deliveries')
    expect(router.currentRoute.value.query).toEqual({ status: 'scheduled' })
  })
})
