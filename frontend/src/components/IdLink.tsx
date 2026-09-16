import type { EntityKind } from '../lib/selection'

interface IdLinkProps {
  kind: EntityKind
  id: string
  onSelect: (kind: EntityKind, id: string) => void
  active?: boolean
  children?: React.ReactNode
}

const WHAT: Record<EntityKind, string> = {
  farm: 'farm',
  client: 'client',
  segment: 'Segment',
}

/** Every ID in the workspace is clickable and leads to the same place. */
export default function IdLink({ kind, id, onSelect, active = false, children }: IdLinkProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(kind, id)}
      aria-label={`Show ${WHAT[kind]} ${id}`}
      className={[
        'rounded underline decoration-dotted underline-offset-2',
        'hover:decoration-solid hover:text-sky-800',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-sky-700',
        active ? 'font-semibold text-sky-900 decoration-solid' : 'text-sky-800',
      ].join(' ')}
    >
      {children ?? id}
    </button>
  )
}
