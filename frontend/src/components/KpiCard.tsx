import type { ReactNode } from 'react'

export type Tone = 'neutral' | 'attention'
export type CardSize = 'lead' | 'support'

interface KpiCardProps {
  label: string
  value: string
  detail?: ReactNode
  tone?: Tone
  /** "lead" cards carry the story, "support" cards carry context with less weight. */
  size?: CardSize
}

export default function KpiCard({ label, value, detail, tone = 'neutral', size = 'lead' }: KpiCardProps) {
  const lead = size === 'lead'
  const attention = tone === 'attention'

  return (
    <div
      className={[
        'rounded-lg border bg-white',
        lead ? 'p-4 shadow-sm' : 'p-3.5',
        attention ? 'border-rose-300 border-l-4 border-l-rose-600' : 'border-slate-200',
      ].join(' ')}
    >
      <div className="flex items-baseline gap-2">
        <p
          className={[
            'font-semibold uppercase tracking-wide',
            lead ? 'text-xs text-slate-600' : 'text-[11px] text-slate-500',
          ].join(' ')}
        >
          {label}
        </p>
        {attention ? (
          <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[11px] font-semibold text-rose-900">
            <span aria-hidden="true">!</span> Needs attention
          </span>
        ) : null}
      </div>

      <p
        className={[
          'mt-1.5 font-semibold tabular-nums text-slate-900',
          lead ? 'text-3xl' : 'text-xl',
        ].join(' ')}
      >
        {value}
      </p>

      {detail ? (
        <div className={lead ? 'mt-1.5 text-sm text-slate-700' : 'mt-1 text-sm text-slate-600'}>
          {detail}
        </div>
      ) : null}
    </div>
  )
}
