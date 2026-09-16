import { formatSignedTonnes, varianceMark } from '../lib/format'

interface VarianceProps {
  value: number
  /** Smaller text, used inside a segment cell next to the actual tonnes. */
  small?: boolean
}

/** A gap is shown with its sign, an arrow and, for screen readers, words. */
export default function Variance({ value, small = false }: VarianceProps) {
  const mark = varianceMark(value)
  const muted = value === 0
  return (
    <span
      className={[
        'whitespace-nowrap tabular-nums',
        small ? 'text-xs' : 'text-sm',
        muted ? 'text-slate-500' : value < 0 ? 'text-rose-800' : 'text-emerald-800',
      ].join(' ')}
    >
      <span aria-hidden="true">{mark.arrow} </span>
      {formatSignedTonnes(value)}
      <span className="sr-only"> {mark.label}</span>
    </span>
  )
}
