import { useRef, type KeyboardEvent, type ReactNode } from 'react'
import type { TabId } from '../lib/selection'

export interface TabDefinition {
  id: TabId
  label: string
  /** Small count shown next to the label, for example "3 at risk". */
  badge?: string
}

interface TabsProps {
  tabs: TabDefinition[]
  active: TabId
  onChange: (id: TabId) => void
  children: ReactNode
}

/** Real ARIA tabs: arrow keys, Home and End move between them. */
export default function Tabs({ tabs, active, onChange, children }: TabsProps) {
  const refs = useRef(new Map<TabId, HTMLButtonElement>())

  function focusTab(id: TabId) {
    onChange(id)
    refs.current.get(id)?.focus()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = tabs.findIndex((tab) => tab.id === active)
    if (index < 0) return

    if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault()
      const step = event.key === 'ArrowRight' ? 1 : -1
      focusTab(tabs[(index + step + tabs.length) % tabs.length].id)
    } else if (event.key === 'Home') {
      event.preventDefault()
      focusTab(tabs[0].id)
    } else if (event.key === 'End') {
      event.preventDefault()
      focusTab(tabs[tabs.length - 1].id)
    }
  }

  return (
    <div>
      <div
        role="tablist"
        aria-label="Plan detail views"
        onKeyDown={handleKeyDown}
        className="flex flex-wrap gap-1 border-b border-slate-300"
      >
        {tabs.map((tab) => {
          const selected = tab.id === active
          return (
            <button
              key={tab.id}
              ref={(node) => {
                if (node) refs.current.set(tab.id, node)
                else refs.current.delete(tab.id)
              }}
              type="button"
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={`panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              className={[
                '-mb-px rounded-t-md border-b-2 px-4 py-2 text-sm font-semibold',
                'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700',
                selected
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-600 hover:border-slate-400 hover:text-slate-900',
              ].join(' ')}
            >
              {tab.label}
              {tab.badge ? (
                <span className="ml-2 rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
                  {tab.badge}
                </span>
              ) : null}
            </button>
          )
        })}
      </div>

      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          tabIndex={0}
          hidden={tab.id !== active}
          className="rounded-b-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
        >
          {tab.id === active ? children : null}
        </div>
      ))}
    </div>
  )
}
