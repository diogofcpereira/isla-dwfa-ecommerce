// src/views/__tests__/LoginView.spec.ts — um 401 mostra a mensagem e NÃO navega.
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import LoginView from '@/views/LoginView.vue'

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

describe('LoginView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('um 401 mostra "Utilizador ou password errados." e fica no /login', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn<typeof globalThis.fetch>()
        .mockResolvedValueOnce(
          json({ detail: 'No active account found with the given credentials' }, 401),
        ),
    )
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/login', name: 'login', component: LoginView },
        { path: '/orders', name: 'orders', component: { template: '<p>orders</p>' } },
      ],
    })
    await router.push('/login?next=/orders')
    const push = vi.spyOn(router, 'push')

    const wrapper = mount(LoginView, { global: { plugins: [createPinia(), router] } })
    await wrapper.find('input[name="username"]').setValue('ana')
    await wrapper.find('input[name="password"]').setValue('errada')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toBe('Utilizador ou password errados.')
    expect(push).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/login')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
  })
})
