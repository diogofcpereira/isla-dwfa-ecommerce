// src/components/__tests__/OrderStatusBadge.spec.ts — um caso por estado do StatusEnum.
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import OrderStatusBadge from '@/components/OrderStatusBadge.vue'
import type { OrderStatus } from '@/types'

describe('OrderStatusBadge', () => {
  it.each<[OrderStatus, string]>([
    ['pending', 'Por pagar'],
    ['paid', 'Paga'],
    ['shipped', 'Enviada'],
    ['cancelled', 'Cancelada'],
  ])('%s → "%s"', (status, label) => {
    const wrapper = mount(OrderStatusBadge, { props: { status } })

    expect(wrapper.text()).toBe(label)
    expect(wrapper.classes()).toContain(status) // a cor vem da classe
  })
})
