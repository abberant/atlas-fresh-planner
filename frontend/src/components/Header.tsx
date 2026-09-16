import type { SourcePayload } from '../api/types'
import { formatClockTime } from '../lib/format'

export type AppStatus = 'idle' | 'loading' | 'ready' | 'invalid' | 'error'

interface HeaderProps {
  status: AppStatus
  source: SourcePayload | null
  sourceFile: string | null
  /** When the browser received the plan. Shown in the header only, never in the plan. */
  loadedAt: Date | null
  errorCount: number
  onReload: () => void
}

interface Badge {
  icon: string
  text: string
  className: string
}

function dataHealth(status: AppStatus, source: SourcePayload | null, errorCount: number): Badge {
  if (status === 'loading') {
    return { icon: '...', text: 'Checking today’s data', className: 'bg-slate-100 text-slate-700' }
  }
  if (status === 'invalid') {
    return {
      icon: '✕',
      text: `Errors: ${errorCount}`,
      className: 'bg-rose-100 text-rose-900',
    }
  }
  if (status === 'error') {
    return { icon: '!', text: 'Server problem', className: 'bg-amber-100 text-amber-900' }
  }
  if (status === 'ready' && source) {
    const farms = source.farms.length
    const clients = source.clients.length
    return {
      icon: '✓',
      text: `Valid: ${farms} farms, ${clients} clients, 1 station`,
      className: 'bg-emerald-100 text-emerald-900',
    }
  }
  return { icon: '–', text: 'No data loaded', className: 'bg-slate-100 text-slate-700' }
}

export default function Header({
  status,
  source,
  sourceFile,
  loadedAt,
  errorCount,
  onReload,
}: HeaderProps) {
  const badge = dataHealth(status, source, errorCount)
  const loading = status === 'loading'
  const label = status === 'idle' ? 'Load today’s data' : 'Reload today’s data'

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-3 px-6 py-3">
        <div className="mr-auto min-w-0">
          <h1 className="text-lg font-semibold text-slate-900">Atlas Fresh</h1>
          <p className="text-sm text-slate-600">Daily apple export planner</p>
          {loadedAt && sourceFile ? (
            <p className="truncate text-xs text-slate-500" title={sourceFile}>
              Loaded at {formatClockTime(loadedAt)} from {sourceFile}
            </p>
          ) : null}
        </div>

        <p className={`rounded-full px-3 py-1 text-sm font-medium ${badge.className}`}>
          <span aria-hidden="true" className="mr-1.5">
            {badge.icon}
          </span>
          {badge.text}
        </p>

        <button
          type="button"
          onClick={onReload}
          disabled={loading}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {loading ? 'Loading…' : label}
        </button>
      </div>
    </header>
  )
}
