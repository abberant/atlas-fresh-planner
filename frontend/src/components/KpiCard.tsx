import type { ReactNode } from 'react'

export type Tone = 'neutral' | 'attention'
export type CardSize = 'lead' | 'support'

interface KpiCardProps {
  label: string
  value: string
  /** Small note next to the value, for a figure that supports it. */
  valueNote?: ReactNode
  detail?: ReactNode
  tone?: Tone
  /** "lead" cards carry the story, "support" cards carry context with less weight. */
  size?: CardSize
}

export default function KpiCard({
  label,
  value,
  valueNote,
  detail,
  tone = 'neutral',
  size = 'lead',
}: KpiCardProps) {
  const lead = size === 'lead'

  return (
    <div
      className={[
        'rounded-lg border border-slate-200 bg-white',
        lead ? 'p-4 shadow-sm' : 'p-3.5',
      ].join(' ')}
    >
      <div className="flex flex-wrap items-baseline gap-2">
        <p
          className={[
            'font-semibold uppercase tracking-wide',
            lead ? 'text-xs text-slate-600' : 'text-[11px] text-slate-500',
          ].join(' ')}
        >
          {label}
        </p>
        {tone === 'attention' ? <AttentionBadge>Needs attention</AttentionBadge> : null}
      </div>

      <p className="mt-1.5 flex flex-wrap items-baseline gap-x-2">
        <span
          className={[
            'font-semibold tabular-nums text-slate-900',
            lead ? 'text-3xl' : 'text-xl',
          ].join(' ')}
        >
          {value}
        </span>
        {valueNote ? <span className="text-sm text-slate-600">{valueNote}</span> : null}
      </p>

      {detail ? (
        <div className={lead ? 'mt-1.5 text-sm text-slate-700' : 'mt-1 text-sm text-slate-600'}>
          {detail}
        </div>
      ) : null}
    </div>
  )
}

/** Status is carried by words and a mark, never by colour on its own. */
export function AttentionBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded bg-rose-100 px-1.5 py-0.5 text-[11px] font-semibold text-rose-900">
      <span aria-hidden="true">!</span>
      {children}
    </span>
  )
}
