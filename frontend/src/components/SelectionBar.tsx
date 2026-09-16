import { isEmpty, selectionChips, type EntityKind, type Selection } from '../lib/selection'

interface SelectionBarProps {
  selection: Selection
  onSetFilter: (kind: EntityKind, id: string | null) => void
  onClear: () => void
}

/** What the user has clicked, with a way back. Drives the tables below. */
export default function SelectionBar({ selection, onSetFilter, onClear }: SelectionBarProps) {
  if (isEmpty(selection)) {
    return (
      <p className="text-sm text-slate-600">
        Click any farm, client or segment id to follow it through the views.
      </p>
    )
  }

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="font-semibold text-slate-700">Following</span>
      {selectionChips(selection).map((chip) => (
        <span
          key={`${chip.kind}-${chip.id}`}
          className="inline-flex items-center gap-1 rounded-full bg-sky-100 py-0.5 pl-3 pr-1 font-medium text-sky-900"
        >
          {chip.label}
          <button
            type="button"
            onClick={() => onSetFilter(chip.kind, null)}
            aria-label={`Stop following ${chip.label}`}
            className="rounded-full px-1.5 text-sky-900 hover:bg-sky-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-sky-700"
          >
            <span aria-hidden="true">&#10005;</span>
          </button>
        </span>
      ))}
      <button
        type="button"
        onClick={onClear}
        className="rounded px-2 py-0.5 font-semibold text-slate-700 underline decoration-dotted underline-offset-2 hover:text-slate-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
      >
        Clear all
      </button>
    </div>
  )
}
