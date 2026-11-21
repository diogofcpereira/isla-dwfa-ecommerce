// src/views/__tests__/CarsView.spec.ts — o catálogo lê a pesquisa do URL e recupera de um erro.
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, page, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Car } from '@/types'
import CarsView from '@/views/CarsView.vue'

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

async function mountAt(url: string) {
  const router = testRouter([{ path: '/cars', name: 'cars', component: CarsView }])
  await router.push(url)
  const wrapper = mount(CarsView, { global: { plugins: [createPinia(), router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('CarsView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('a pesquisa, o combustível e a página do URL vão para o pedido', async () => {
    const fetch = stubFetch(json(page([golf], 41)))
    const { wrapper } = await mountAt('/cars?search=golf&fuel=petrol&page=2')

    const url = new URL(requestAt(fetch, 0).url)
    expect(url.pathname).toBe('/api/v1/cars/')
    expect(url.searchParams.get('search')).toBe('golf')
    expect(url.searchParams.get('fuel')).toBe('petrol')
    expect(url.searchParams.get('page')).toBe('2')
    expect(wrapper.text()).toContain('Volkswagen Golf')
    expect(wrapper.text()).toContain('Página 2 de 3') // 41 viaturas, 20 por página
  })

  it('pesquisar escreve no URL e volta à página 1', async () => {
    stubFetch(json(page([golf], 41)), json(page([])))
    const { wrapper, router } = await mountAt('/cars?page=2')

    await wrapper.find('input[name="search"]').setValue('tesla') // .lazy: dispara no change
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ search: 'tesla' })
    expect(wrapper.text()).toContain('Nenhuma viatura corresponde à pesquisa.')
  })

  it('um erro de rede mostra "Tentar de novo", que repete o pedido', async () => {
    const fetch = vi
      .fn<typeof globalThis.fetch>()
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(json(page([golf])))
    vi.stubGlobal('fetch', fetch)
    const { wrapper } = await mountAt('/cars')

    expect(wrapper.find('[role="alert"]').text()).toContain('Sem ligação à API')
    await wrapper.find('[role="alert"] button').trigger('click')
    await flushPromises()

    expect(fetch).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Volkswagen Golf')
  })
})
