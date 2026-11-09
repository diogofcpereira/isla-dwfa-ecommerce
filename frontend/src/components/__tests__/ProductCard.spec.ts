// src/components/__tests__/ProductCard.spec.ts
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ProductCard from '@/components/ProductCard.vue'
import type { Product } from '@/types'

const product: Product = {
  id: 7,
  category: 1,
  category_name: 'Candeeiros',
  sku: 'SKU-0007',
  name: '<b>Lamp</b>',
  price: '9.90',
  stock: 3,
  is_active: true,
  created_at: '2026-11-02T19:00:00Z',
}

describe('ProductCard', () => {
  it('mostra o nome como texto, sem interpretar HTML', () => {
    const wrapper = mount(ProductCard, { props: { product } })

    expect(wrapper.find('h3').text()).toBe('<b>Lamp</b>') // os sinais < > aparecem
    expect(wrapper.find('b').exists()).toBe(false) // não foi criado nenhum <b>
    expect(wrapper.text()).toContain('9.90 €')
  })

  it('emite select com o id quando se clica', async () => {
    const wrapper = mount(ProductCard, { props: { product } })

    await wrapper.find('article').trigger('click')

    expect(wrapper.emitted('select')).toEqual([[7]])
  })
})
