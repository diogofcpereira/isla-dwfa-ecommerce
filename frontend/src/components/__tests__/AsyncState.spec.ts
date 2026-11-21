// src/components/__tests__/AsyncState.spec.ts — os 4 estados de um ecrã.
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AsyncState from '@/components/AsyncState.vue'

const slots = { default: '<p class="data">dados</p>' }

describe('AsyncState', () => {
  it('a carregar: mostra "A carregar…" e não os dados', () => {
    const wrapper = mount(AsyncState, { props: { status: 'loading', error: null }, slots })
    expect(wrapper.text()).toContain('A carregar…')
    expect(wrapper.find('.data').exists()).toBe(false)
  })

  it('erro: mostra a mensagem e "Tentar de novo" emite retry', async () => {
    const wrapper = mount(AsyncState, {
      props: { status: 'error', error: 'Sem ligação à API.' },
      slots,
    })
    expect(wrapper.find('[role="alert"]').text()).toContain('Sem ligação à API.')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('vazio: mostra o texto de vazio; com dados: mostra o slot', async () => {
    const wrapper = mount(AsyncState, {
      props: { status: 'ok', error: null, empty: true, emptyText: 'Nada aqui.' },
      slots,
    })
    expect(wrapper.text()).toContain('Nada aqui.')
    await wrapper.setProps({ empty: false })
    expect(wrapper.find('.data').exists()).toBe(true)
  })
})
