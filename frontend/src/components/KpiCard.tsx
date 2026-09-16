export type Tone = 'neutral' | 'good' | 'warn' | 'risk'

const TONE_STYLES: Record<Tone, string> = {
  neutral: 'border-l-slate-300',
  good: 'border-l-emerald-600',
  warn: 'border-l-amber-500',
  risk: 'border-l-rose-600',
}

interface KpiCardProps {
  label: string
  value: string
  detail?: string
  tone?: Tone
  /** Fills the rest of the row, so the grid never ends with a gap. */
  wide?: boolean
}

export default function KpiCard({ label, value, detail, tone = 'neutral', wide = false }: KpiCardProps) {
  return (
    <div
      className={[
        'rounded-lg border border-slate-200 border-l-4 bg-white p-4 shadow-sm',
        TONE_STYLES[tone],
        wide ? 'sm:col-span-2 lg:col-span-3 xl:col-span-2' : '',
      ].join(' ')}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-900 tabular-nums">{value}</p>
      {detail ? <p className="mt-1 text-sm text-slate-600">{detail}</p> : null}
    </div>
  )
}
