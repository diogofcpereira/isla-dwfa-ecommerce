// src/views/__tests__/CarView.spec.ts — o painel do gestor: só para gestores, e com erros por campo.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, problem400, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Car } from '@/types'
import CarView from '@/views/CarView.vue'

const golf: Car = {
  id: 1,
  brand: 1,
  brand_name: 'Volkswagen',
  code: 'DN-0001',
  model: 'Golf',
  version: '1.5 eTSI Life',
  year: 2025,
  fuel: 'petrol',
  fuel_display: 'Gasolina',
  price: '32500.00',
  stock: 10,
  is_active: true,
  created_at: '2026-11-20T10:00:00Z',
}

async function mountCar() {
  const router = testRouter([{ path: '/cars/:id', name: 'car', component: CarView, props: true }])
  await router.push('/cars/1')
  const wrapper = mount(CarView, { props: { id: '1' }, global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('CarView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('um cliente vê o detalhe mas não o painel de gestão', async () => {
    loginAs('ana')
    stubFetch(json(golf))
    const wrapper = await mountCar()

    expect(wrapper.find('h1').text()).toBe('Volkswagen Golf')
    expect(wrapper.text()).toContain('DN-0001')
    expect(wrapper.find('form.panel').exists()).toBe(false)
  })

  it('o gestor guarda e um 400 mostra o erro ao lado do campo do preço', async () => {
    loginAs('gestor', ['gestores'])
    const fetch = stubFetch(json(golf), problem400({ price: ['O preço tem de ser positivo.'] }))
    const wrapper = await mountCar()

    await wrapper.find('input[name="price"]').setValue('-1')
    await wrapper.find('form.panel').trigger('submit')
    await flushPromises()

    const patch = requestAt(fetch, 1)
    expect(patch.method).toBe('PATCH')
    expect(await patch.json()).toMatchObject({ price: '-1', stock: 10, is_active: true })
    expect(wrapper.find('#price-error').text()).toBe('O preço tem de ser positivo.')
    expect(wrapper.find('input[name="price"]').attributes('aria-invalid')).toBe('true')
  })
})
