// e2e/percurso.spec.ts — o fluxo de negócio de ponta a ponta, com dois utilizadores ao mesmo
// tempo (dois browsers): a Ana encomenda e paga; o gestor agenda, expede e conclui a entrega;
// a Ana vê a encomenda entregue.
import { expect, test } from '@playwright/test'

import { signIn, tomorrowAt10, watchErrors } from './helpers'

test('encomenda → pagamento → entrega agendada → expedida → entregue', async ({ browser }) => {
  const anaContext = await browser.newContext()
  const gestorContext = await browser.newContext()
  const ana = await anaContext.newPage()
  const gestor = await gestorContext.newPage()
  const errors = { ana: watchErrors(ana), gestor: watchErrors(gestor) }

  // ---- a Ana encomenda uma viatura e paga ----
  await ana.goto('/orders/new')
  await signIn(ana, 'ana') // /login?next=/orders/new → volta à nova encomenda
  await expect(ana.getByRole('heading', { name: 'Nova encomenda' })).toBeVisible()
  const golf = ana.getByLabel('Viatura').locator('option', { hasText: 'Volkswagen Golf' })
  await ana
    .getByLabel('Viatura')
    .selectOption(await golf.evaluate((o) => (o as HTMLOptionElement).value))
  await ana.getByRole('button', { name: 'Criar encomenda' }).click()

  await expect(ana).toHaveURL(/\/orders\?status=pending&created=\d+$/)
  const orderId = new URL(ana.url()).searchParams.get('created') ?? ''
  const mine = new RegExp(`#${orderId}(?!\\d)`) // #31, e não #310
  const order = ana.locator('article.order', { hasText: mine })
  await order.getByLabel('Pagamento').selectOption({ label: 'MB WAY' })
  await order.getByRole('button', { name: 'Pagar', exact: true }).click()
  await expect(ana.getByRole('status')).toContainText(`Encomenda #${orderId} paga`)

  // ---- o gestor agenda a entrega, expede e conclui ----
  await gestor.goto('/deliveries/new')
  await signIn(gestor, 'gestor')
  await expect(gestor.getByRole('heading', { name: 'Agendar entrega' })).toBeVisible()
  await gestor.getByLabel('Encomenda paga').selectOption(orderId)
  await gestor.getByLabel('Data e hora').fill(tomorrowAt10())
  await gestor.getByLabel('Morada').fill('Rua das Flores, 10, Porto')
  await gestor.getByRole('button', { name: 'Agendar' }).click()

  await expect(gestor).toHaveURL(/\/deliveries\?status=scheduled$/)
  await expect(gestor.getByRole('list', { name: 'Resumo das entregas' })).toBeVisible()
  const row = gestor.getByRole('row', { name: mine })
  await row.getByRole('button', { name: 'Expedir' }).click()
  await expect(row).toContainText('Em trânsito')
  await row.getByRole('button', { name: 'Concluir' }).click()
  await expect(row).toContainText('Entregue')

  // ---- a Ana vê a entrega concluída e a encomenda entregue ----
  await ana.goto('/deliveries')
  const anaRow = ana.getByRole('row', { name: mine })
  await expect(anaRow).toContainText('Entregue')
  await ana.goto('/orders?status=delivered')
  await expect(ana.locator('article.order', { hasText: mine })).toContainText('Entregue')

  expect(errors).toEqual({ ana: [], gestor: [] })
  await anaContext.close()
  await gestorContext.close()
})
