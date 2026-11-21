// src/utils/format.ts — formatação para o ecrã, num só sítio (pt-PT, euros).
// Os valores chegam da API como texto ("32500.00"): só se convertem para mostrar.
const euros = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' })

/** "32500.00" → "32 500,00 €" */
export function money(value: string | number): string {
  return euros.format(Number(value))
}

/** ISO 8601 → "20/11/2026, 10:00" */
export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' })
}
