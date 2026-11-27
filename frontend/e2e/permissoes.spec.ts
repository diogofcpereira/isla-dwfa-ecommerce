// e2e/permissoes.spec.ts — rota privada → login → volta; a sessão sobrevive a um F5;
// um cliente numa rota de gestor vai para /forbidden.
import { expect, test } from '@playwright/test'

import { signIn, watchErrors } from './helpers'

test('rota privada sem sessão: login e volta; F5 mantém a sessão; cliente → /forbidden', async ({
  page,
}) => {
  const errors = watchErrors(page)
  await page.goto('/orders')
  await expect(page).toHaveURL(/\/login\?next=\/orders$/)

  await signIn(page, 'ana')
  await expect(page).toHaveURL(/\/orders$/)
  await expect(page.getByRole('heading', { name: 'As minhas encomendas' })).toBeVisible()

  await page.reload() // o refresh no localStorage renova o access antes de montar a app
  await expect(page.getByRole('heading', { name: 'As minhas encomendas' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Sair' })).toBeVisible()

  await page.goto('/deliveries/new') // só gestores
  await expect(page).toHaveURL(/\/forbidden$/)
  await expect(page.getByRole('heading', { name: 'Sem permissão' })).toBeVisible()
  expect(errors).toEqual([])
})
