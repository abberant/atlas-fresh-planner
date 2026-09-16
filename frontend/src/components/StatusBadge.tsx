import type { ClientStatus } from '../api/types'

const STYLES: Record<ClientStatus, { icon: string; text: string; className: string }> = {
  COMPLETE: { icon: '✓', text: 'Complete', className: 'bg-emerald-100 text-emerald-900' },
  PARTIAL: { icon: '!', text: 'Partial', className: 'bg-rose-100 text-rose-900' },
  UNSERVED: { icon: '✕', text: 'Unserved', className: 'bg-rose-200 text-rose-950' },
}

/** Status is always a word plus a mark, never a colour on its own. */
export default function StatusBadge({ status }: { status: ClientStatus }) {
  const style = STYLES[status]
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded px-2 py-0.5 text-xs font-semibold ${style.className}`}
    >
      <span aria-hidden="true">{style.icon}</span>
      {style.text}
    </span>
  )
}
