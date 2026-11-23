// src/views/__tests__/DeliveriesView.spec.ts — o cliente só acompanha; o gestor expede e conclui.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Delivery } from '@/types'
import DeliveriesView from '@/views/DeliveriesView.vue'

const scheduled: Delivery = {
  id: 5,
  order: 12,
  customer: 1,
  status: 'scheduled',
  status_display: 'Agendada',
  scheduled_for: '2026-11-25T10:00:00Z',
  address: 'Rua das Flores, 10, Porto',
  notes: '',
  delivered_at: null,
  created_at: '2026-11-20T10:00:00Z',
}

async function mountAs(username: string, groups: string[] = [], url = '/deliveries') {
  loginAs(username, groups)
  const router = testRouter([
    { path: '/deliveries', name: 'deliveries', component: DeliveriesView },
  ])
  await router.push(url)
  const wrapper = mount(DeliveriesView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('DeliveriesView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('o cliente vê as suas entregas sem botões de gestão; o filtro vem do URL', async () => {
    const fetch = stubFetch(json(page([scheduled])))
    const wrapper = await mountAs('ana', [], '/deliveries?status=scheduled')

    expect(new URL(requestAt(fetch, 0).url).searchParams.get('status')).toBe('scheduled')
    expect(wrapper.find('h1').text()).toBe('As minhas entregas')
    expect(wrapper.text()).toContain('Rua das Flores, 10, Porto')
    expect(wrapper.find('button').exists()).toBe(false) // nem Expedir nem Agendar
    expect(wrapper.text()).not.toContain('Agendar entrega')
  })

  it('o gestor expede: POST /ship/ e a linha passa a "Em trânsito"', async () => {
    const fetch = stubFetch(
      json(page([scheduled])),
      json({ ...scheduled, status: 'in_transit', status_display: 'Em trânsito' }),
    )
    const wrapper = await mountAs('gestor', ['gestores'])

    await wrapper.find('tbody button').trigger('click')
    await flushPromises()

    const post = requestAt(fetch, 1)
    expect(post.method).toBe('POST')
    expect(new URL(post.url).pathname).toBe('/api/v1/deliveries/5/ship/')
    expect(wrapper.text()).toContain('Em trânsito')
    expect(wrapper.find('tbody button').text()).toBe('Concluir')
  })

  it('um 409 do gestor (estado já mudou) mostra a mensagem na linha', async () => {
    stubFetch(
      json(page([scheduled])),
      json({ title: 'Conflict', status: 409, detail: "A entrega está 'Entregue'." }, 409),
    )
    const wrapper = await mountAs('gestor', ['gestores'])

    await wrapper.find('tbody button').trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe("A entrega está 'Entregue'.")
  })
})
