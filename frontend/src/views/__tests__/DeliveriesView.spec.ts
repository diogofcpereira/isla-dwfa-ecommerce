// src/views/__tests__/DeliveriesView.spec.ts — o cliente só acompanha; o gestor expede e conclui.
// M2 (extra): o resumo do gestor e o filtro "Só em atraso".
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Delivery, DeliverySummary } from '@/types'
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
  is_overdue: false,
  created_at: '2026-11-20T10:00:00Z',
}
const summary: DeliverySummary = { scheduled: 3, in_transit: 1, delivered: 5, overdue: 2 }

async function mountAs(username: string, groups: string[] = [], url = '/deliveries') {
  loginAs(username, groups)
  const router = testRouter([
    { path: '/deliveries', name: 'deliveries', component: DeliveriesView },
  ])
  await router.push(url)
  const wrapper = mount(DeliveriesView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

describe('DeliveriesView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('o cliente vê as suas entregas sem botões de gestão; o filtro vem do URL', async () => {
    const fetch = stubFetch(json(page([scheduled])))
    const { wrapper } = await mountAs('ana', [], '/deliveries?status=scheduled')

    expect(fetch).toHaveBeenCalledTimes(1) // o cliente não pede o resumo
    expect(new URL(requestAt(fetch, 0).url).searchParams.get('status')).toBe('scheduled')
    expect(wrapper.find('h1').text()).toBe('As minhas entregas')
    expect(wrapper.text()).toContain('Rua das Flores, 10, Porto')
    expect(wrapper.find('button').exists()).toBe(false) // nem Expedir nem Agendar
    expect(wrapper.text()).not.toContain('Agendar entrega')
    expect(wrapper.find('.summary').exists()).toBe(false)
  })

  it('o gestor expede: POST /ship/, a linha passa a "Em trânsito" e o resumo atualiza', async () => {
    const fetch = stubFetch(
      json(page([scheduled])),
      json(summary),
      json({ ...scheduled, status: 'in_transit', status_display: 'Em trânsito' }),
      json({ ...summary, scheduled: 2, in_transit: 2 }),
    )
    const { wrapper } = await mountAs('gestor', ['gestores'])

    await wrapper.find('tbody button').trigger('click')
    await flushPromises()

    const post = requestAt(fetch, 2)
    expect(post.method).toBe('POST')
    expect(new URL(post.url).pathname).toBe('/api/v1/deliveries/5/ship/')
    expect(wrapper.text()).toContain('Em trânsito')
    expect(wrapper.find('tbody button').text()).toBe('Concluir')
    expect(new URL(requestAt(fetch, 3).url).pathname).toBe('/api/v1/deliveries/summary/')
    expect(wrapper.find('.summary').text()).toContain('2 Em trânsito')
  })

  it('um 409 do gestor (estado já mudou) mostra a mensagem na linha', async () => {
    stubFetch(
      json(page([scheduled])),
      json(summary),
      json({ title: 'Conflict', status: 409, detail: "A entrega está 'Entregue'." }, 409),
    )
    const { wrapper } = await mountAs('gestor', ['gestores'])

    await wrapper.find('tbody button').trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe("A entrega está 'Entregue'.")
  })

  it('o gestor vê o resumo; cada número leva à lista filtrada e o atraso fica em destaque', async () => {
    const fetch = stubFetch(json(page([scheduled])), json(summary))
    const { wrapper } = await mountAs('gestor', ['gestores'])

    expect(new URL(requestAt(fetch, 1).url).pathname).toBe('/api/v1/deliveries/summary/')
    const links = wrapper.findAll('.summary a')
    expect(links.map((a) => a.text())).toEqual([
      '3 Agendadas',
      '1 Em trânsito',
      '5 Entregues',
      '2 Em atraso',
    ])
    expect(links[0]?.attributes('href')).toBe('/deliveries?status=scheduled')
    expect(links[3]?.attributes('href')).toBe('/deliveries?overdue=true')
    expect(links[3]?.classes()).toContain('alert')
  })

  it('"Só em atraso" vai para o URL e para a API; a linha mostra "Em atraso"', async () => {
    const late = { ...scheduled, is_overdue: true }
    const fetch = stubFetch(json(page([scheduled])), json(page([late])))
    const { wrapper, router } = await mountAs('ana')

    await wrapper.find('input[name="overdue"]').setValue(true)
    await flushPromises()

    expect(router.currentRoute.value.query.overdue).toBe('true')
    expect(new URL(requestAt(fetch, 1).url).searchParams.get('overdue')).toBe('true')
    expect(wrapper.find('tbody').text()).toContain('Em atraso')
  })
})
