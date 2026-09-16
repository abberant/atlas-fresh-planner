/** Number formatting for the workspace. English locale, one shape everywhere. */

const NUMBER = new Intl.NumberFormat('en-US')
const ONE_DECIMAL = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

/** Tonnes with one decimal only when the value needs it: "560 t", "11.7 t". */
export function formatTonnes(value: number, unit = true): string {
  const rounded = Math.round(value * 10) / 10
  const text = Number.isInteger(rounded) ? NUMBER.format(rounded) : ONE_DECIMAL.format(rounded)
  return unit ? `${text} t` : text
}

/** Tonnes with an explicit sign, for a gap against plan: "+7.9 t", "-11.7 t". */
export function formatSignedTonnes(value: number, unit = true): string {
  const rounded = Math.round(value * 10) / 10
  if (rounded === 0) return unit ? '0 t' : '0'
  const sign = rounded > 0 ? '+' : '-'
  return `${sign}${formatTonnes(Math.abs(rounded), unit)}`
}

/** Euros, no cents: "EUR 549,500". */
export function formatEur(value: number): string {
  return `EUR ${NUMBER.format(Math.round(value))}`
}

/** A fraction as a percent: 0.893 becomes "89.3%", 1 becomes "100%". Null becomes "n/a". */
export function formatPercent(fraction: number | null): string {
  if (fraction === null || Number.isNaN(fraction)) return 'n/a'
  const percent = Math.round(fraction * 1000) / 10
  const text = Number.isInteger(percent) ? NUMBER.format(percent) : ONE_DECIMAL.format(percent)
  return `${text}%`
}

/** "03:25", the moment the plan was loaded in the browser. Never part of the plan. */
export function formatClockTime(date: Date): string {
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

/** An arrow and a word, so a gap is never shown by colour alone. */
export function varianceMark(value: number): { arrow: string; label: string } {
  if (value > 0) return { arrow: '▲', label: 'above plan' }
  if (value < 0) return { arrow: '▼', label: 'below plan' }
  return { arrow: '=', label: 'on plan' }
}

/** "A", "A and B", "A, B and C" */
export function joinWithAnd(parts: string[]): string {
  if (parts.length === 0) return ''
  if (parts.length === 1) return parts[0]
  return `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`
}
