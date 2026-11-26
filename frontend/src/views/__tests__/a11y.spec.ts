// src/views/__tests__/a11y.spec.ts — acessibilidade automática (axe-core, WCAG 2.1 A/AA) nos
// ecrãs com formulários e listas: cada campo com nome, erros ligados ao campo, sem roles inválidos.
// Os ecrãs são montados no documento (attachTo) com os dados e os erros já à vista.
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Component } from 'vue'

import {
  a11yViolations,
  json,
  loginAs,
  page,
  problem400,
  stubFetch,
  testRouter,
} from '@/test/helpers'
import App from '@/App.vue'
import type { Car, Order } from '@/types'
import CarsView from '@/views/CarsView.vue'
import LoginView from '@/views/LoginView.vue'
import NewDeliveryView from '@/views/NewDeliveryView.vue'
import NewOrderView from '@/views/NewOrderView.vue'
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
const paid: Order = {
  id: 12,
  customer: 1,
  status: 'paid',
  created_at: '2026-11-20T10:00:00Z',
  items: [{ id: 1, car: 1, car_name: 'Volkswagen Golf', quantity: 1, unit_price: '32500.00' }],
  total: '32500.00',
}

/** Monta o ecrã numa rota, ligado ao documento, e espera pelos pedidos. */
async function mountScreen(component: Component, path: string, name: string) {
  const router = testRouter([{ path, name, component }])
  await router.push(path)
  const wrapper = mount(component, { attachTo: document.body, global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('acessibilidade (axe-core)', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('login, com o erro de credenciais à vista', async () => {
    stubFetch(json({ detail: 'No active account found with the given credentials' }, 401))
    const router = testRouter([{ path: '/login', name: 'login', component: LoginView }])
    await router.push('/login')
    const wrapper = mount(LoginView, {
      attachTo: document.body,
      global: { plugins: [createPinia(), router] },
    })
    await wrapper.find('input[name="username"]').setValue('ana')
    await wrapper.find('input[name="password"]').setValue('errada')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
    expect(await a11yViolations(wrapper.element)).toEqual([])
  })

  it('catálogo, com pesquisa, filtro e paginação', async () => {
    loginAs('ana')
    stubFetch(json(page([golf], 41)))
    const wrapper = await mountScreen(CarsView, '/cars', 'cars')

    expect(wrapper.text()).toContain('Volkswagen Golf')
    expect(await a11yViolations(wrapper.element)).toEqual([])
  })

  it('nova encomenda, com os erros da API nas linhas', async () => {
    loginAs('ana')
    stubFetch(
      json(page([golf])),
      problem400({ items: { '0': { quantity: ['Só há 10 em stock.'] } } }),
    )
    const wrapper = await mountScreen(NewOrderView, '/orders/new', 'new-order')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(await a11yViolations(wrapper.element)).toEqual([])
  })

  it('test drives do cliente, com o formulário de marcação', async () => {
    loginAs('ana')
    stubFetch(json(page([])), json(page([golf])))
    const wrapper = await mountScreen(TestDrivesView, '/test-drives', 'test-drives')

    expect(wrapper.find('form.card').exists()).toBe(true)
    expect(await a11yViolations(wrapper.element)).toEqual([])
  })

  it('agendar entrega (gestor), com erros por campo', async () => {
    loginAs('gestor', ['gestores'])
    stubFetch(
      json(page([paid])),
      problem400({ scheduled_for: ['A data da entrega tem de ser no futuro.'] }),
    )
    const wrapper = await mountScreen(NewDeliveryView, '/deliveries/new', 'new-delivery')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('#scheduled-error').exists()).toBe(true)
    expect(await a11yViolations(wrapper.element)).toEqual([])
  })
})

describe('acessibilidade da moldura da app', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
  })

  it('tem o atalho "Saltar para o conteúdo" e, ao mudar de ecrã, o foco vai para o conteúdo', async () => {
    loginAs('ana')
    const screen = (text: string) => ({ template: `<h1>${text}</h1>` })
    const router = testRouter([
      { path: '/cars', name: 'cars', component: screen('Viaturas') },
      { path: '/orders', name: 'orders', component: screen('Encomendas') },
    ])
    await router.push('/cars')
    const wrapper = mount(App, { attachTo: document.body, global: { plugins: [router] } })
    await flushPromises()

    const skip = wrapper.find('a.skip-link')
    expect(skip.attributes('href')).toBe('#conteudo')
    expect(document.activeElement).not.toBe(document.getElementById('conteudo')) // no arranque não

    await router.push('/orders')
    await flushPromises()
    expect(document.activeElement).toBe(document.getElementById('conteudo'))

    ;(skip.element as HTMLElement).focus() // ex.: o cursor está no campo de pesquisa
    await router.push('/orders?status=paid') // só muda a query: o foco fica onde estava
    await flushPromises()
    expect(document.activeElement).toBe(skip.element)
    expect(await a11yViolations(document.body)).toEqual([])
  })
})
