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

/** O valor de um <input type="datetime-local"> ("2026-11-25T10:00", hora local) → ISO 8601. */
export function localToIso(value: string): string {
  return new Date(value).toISOString()
}

/** 4 → "★★★★☆" (com o número para leitores de ecrã no aria-label de quem o usa). */
export function stars(rating: number): string {
  const n = Math.max(0, Math.min(5, Math.round(rating)))
  return '★'.repeat(n) + '☆'.repeat(5 - n)
}
