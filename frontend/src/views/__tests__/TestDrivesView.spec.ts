// src/views/__tests__/TestDrivesView.spec.ts — marcar com erros no campo, pesquisar e confirmar.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, problem400, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Car, TestDrive } from '@/types'
import TestDrivesView from '@/views/TestDrivesView.vue'

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
const requested: TestDrive = {
  id: 4,
  car: 1,
  car_name: 'Volkswagen Golf 1.5 eTSI Life',
  customer: 1,
  scheduled_for: '2026-11-28T10:00:00Z',
  status: 'requested',
  status_display: 'Pedido',
  notes: '',
  created_at: '2026-11-20T10:00:00Z',
}

async function mountAs(groups: string[], url: string, ...responses: Response[]) {
  loginAs(groups.length ? 'gestor' : 'ana', groups)
  const fetch = stubFetch(...responses)
  const router = testRouter([
    { path: '/test-drives', name: 'test-drives', component: TestDrivesView },
  ])
  await router.push(url)
  const wrapper = mount(TestDrivesView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, fetch, router }
}

const urlOf = (fetch: ReturnType<typeof stubFetch>, n: number) => new URL(requestAt(fetch, n).url)

describe('TestDrivesView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('o cliente marca dia + hora certa; um horário ocupado mostra o erro no campo', async () => {
    // Ordem dos pedidos: a lista (useFetch) e as viaturas do formulário.
    const { wrapper, fetch } = await mountAs(
      [],
      '/test-drives',
      json(page([])),
      json(page([golf])),
      problem400({ scheduled_for: ['Este horário já está marcado para esta viatura.'] }),
    )
    const paths = [0, 1].map((n) => urlOf(fetch, n).pathname).sort()
    expect(paths).toEqual(['/api/v1/cars/', '/api/v1/test-drives/'])

    await wrapper.find('select[name="car"]').setValue(1)
    await wrapper.find('input[name="day"]').setValue('2026-11-28')
    await wrapper.find('select[name="hour"]').setValue(15)
    await wrapper.find('form.card').trigger('submit')
    await flushPromises()

    expect(await requestAt(fetch, 2).json()).toEqual({
      car: 1,
      scheduled_for: new Date('2026-11-28T15:00').toISOString(),
      notes: '',
    })
    expect(wrapper.find('#scheduled-error').text()).toBe(
      'Este horário já está marcado para esta viatura.',
    )
  })

  it('a pesquisa do URL vai para a API (?search=) e pesquisar volta à página 1', async () => {
    const { wrapper, fetch, router } = await mountAs(
      ['gestores'],
      '/test-drives?search=golf&page=2',
      json(page([requested], 25)),
      json(page([])),
    )

    expect(urlOf(fetch, 0).searchParams.get('search')).toBe('golf')
    expect(urlOf(fetch, 0).searchParams.get('page')).toBe('2')
    expect(wrapper.find('form.card').exists()).toBe(false) // o gestor não marca

    await wrapper.find('input[name="search"]').setValue('ana')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ search: 'ana' })
    expect(urlOf(fetch, 1).searchParams.get('search')).toBe('ana')
  })

  it('o gestor confirma um pedido: POST /confirm/ e o estado muda na linha', async () => {
    const { wrapper, fetch } = await mountAs(
      ['gestores'],
      '/test-drives',
      json(page([requested])),
      json({ ...requested, status: 'confirmed', status_display: 'Confirmado' }),
    )

    await wrapper
      .findAll('button')
      .find((b) => b.text() === 'Confirmar')!
      .trigger('click')
    await flushPromises()

    expect(urlOf(fetch, 1).pathname).toBe('/api/v1/test-drives/4/confirm/')
    expect(wrapper.text()).toContain('Confirmado')
    expect(wrapper.findAll('button').some((b) => b.text() === 'Confirmar')).toBe(false)
  })
})
