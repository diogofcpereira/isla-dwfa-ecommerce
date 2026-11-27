// e2e/catalogo.spec.ts — o visitante (sem sessão): pesquisa, detalhe e F5 numa rota da SPA.
import { expect, test } from '@playwright/test'

import { watchErrors } from './helpers'

test('pesquisa no catálogo, abre o detalhe e um F5 mostra o mesmo ecrã', async ({ page }) => {
  const errors = watchErrors(page)
  await page.goto('/cars')
  await expect(page).toHaveTitle('Viaturas · DriveNow')

  await page.getByLabel('Pesquisar').fill('golf')
  await page.getByLabel('Pesquisar').press('Enter')
  await expect(page).toHaveURL(/\/cars\?search=golf/) // o estado da lista vive no URL
  await expect(page.getByText('1 viaturas')).toBeVisible()

  await page.getByRole('link', { name: 'Volkswagen Golf' }).click()
  await expect(page).toHaveURL(/\/cars\/\d+$/)
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Volkswagen Golf')

  await page.reload() // o Nginx devolve o index.html (try_files) e o Vue Router mostra o ecrã
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Volkswagen Golf')
  expect(errors).toEqual([])
})
