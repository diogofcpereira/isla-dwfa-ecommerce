// src/views/__tests__/ReviewModerationView.spec.ts — o gestor aprova e corrige sem mudar o estado.
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { json, loginAs, page, requestAt, stubFetch, testRouter } from '@/test/helpers'
import type { Review } from '@/types'
import ReviewModerationView from '@/views/ReviewModerationView.vue'

const pending: Review = {
  id: 9,
  car: 13,
  car_name: 'Toyota Yaris',
  customer: 7,
  rating: 4,
  comment: 'Liguem-me para o 912 345 678.',
  status: 'pending',
  status_display: 'Pendente',
  created_at: '2026-11-20T10:00:00Z',
}

async function mountModeration(url = '/reviews/moderation', ...responses: Response[]) {
  loginAs('gestor', ['gestores'])
  const fetch = stubFetch(...responses)
  const router = testRouter([
    { path: '/reviews/moderation', name: 'review-moderation', component: ReviewModerationView },
  ])
  await router.push(url)
  const wrapper = mount(ReviewModerationView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, fetch }
}

const button = (wrapper: Awaited<ReturnType<typeof mountModeration>>['wrapper'], text: string) =>
  wrapper.findAll('button').find((b) => b.text() === text)!

describe('ReviewModerationView', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('abre nas pendentes e "Aprovar" envia {"status": "approved"}', async () => {
    const { wrapper, fetch } = await mountModeration(
      '/reviews/moderation',
      json(page([pending])),
      json({ ...pending, status: 'approved', status_display: 'Aprovada' }),
    )

    expect(new URL(requestAt(fetch, 0).url).searchParams.get('status')).toBe('pending')
    await button(wrapper, 'Aprovar').trigger('click')
    await flushPromises()

    const post = requestAt(fetch, 1)
    expect(new URL(post.url).pathname).toBe('/api/v1/reviews/9/moderate/')
    expect(await post.json()).toEqual({ status: 'approved' })
    expect(wrapper.text()).toContain('Aprovada')
  })

  it('corrigir o comentário de uma aprovada envia só o comentário e ela continua aprovada', async () => {
    const approved = { ...pending, status: 'approved' as const, status_display: 'Aprovada' }
    const { wrapper, fetch } = await mountModeration(
      '/reviews/moderation?status=approved',
      json(page([approved])),
      json({ ...approved, comment: 'Liguem-me.' }), // a API (M2) mantém o estado
    )

    await button(wrapper, 'Corrigir comentário').trigger('click')
    await wrapper.find('textarea[name="moderation-comment"]').setValue('Liguem-me.')
    await button(wrapper, 'Guardar').trigger('click')
    await flushPromises()

    expect(await requestAt(fetch, 1).json()).toEqual({ comment: 'Liguem-me.' })
    expect(wrapper.text()).toContain('Aprovada')
    expect(wrapper.text()).toContain('Liguem-me.')
  })
})
