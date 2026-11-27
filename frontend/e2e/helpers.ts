// e2e/helpers.ts — o que os testes e2e partilham.
import { expect, type Page } from '@playwright/test'

/** As contas do `manage.py seed` (README · Credenciais de demonstração). */
export const PASSWORD = 'drivenow-demo-2026'

/**
 * Regista os erros da página: exceções de JavaScript e violações da CSP (o browser recusa
 * um script ou um estilo que não venha da nossa origem). No fim do teste, `expect(…).toEqual([])`.
 */
export function watchErrors(page: Page): string[] {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(`JS: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() === 'error' && m.text().includes('Content Security Policy')) {
      errors.push(`CSP: ${m.text()}`)
    }
  })
  return errors
}

/** Preenche o formulário de login (a página já tem de estar em /login). */
export async function signIn(page: Page, username: string) {
  await expect(page.getByRole('heading', { name: 'Entrar' })).toBeVisible()
  await page.getByLabel('Utilizador').fill(username)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Entrar' }).click()
}

/** Uma data no formato do <input type="datetime-local">: amanhã, às 10:00. */
export function tomorrowAt10(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T10:00`
}
