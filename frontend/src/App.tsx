import { useCallback, useState } from 'react'
import { ApiError, loadSeedPlan, type ApiErrorKind } from './api/client'
import type { PlanResponse, ValidationIssue } from './api/types'
import DecisionSummary from './components/DecisionSummary'
import EmptyState from './components/EmptyState'
import ErrorBanner from './components/ErrorBanner'
import Header, { type AppStatus } from './components/Header'
import LoadingSkeleton from './components/LoadingSkeleton'
import SelectionBar from './components/SelectionBar'
import Tabs, { type TabDefinition } from './components/Tabs'
import ValidationErrorPanel from './components/ValidationErrorPanel'
import WhatChanged from './components/WhatChanged'
import {
  NO_SELECTION,
  setFilter,
  TAB_FOR_KIND,
  withSelection,
  type EntityKind,
  type Selection,
  type TabId,
} from './lib/selection'
import AllocationsView from './views/AllocationsView'
import CommercialView from './views/CommercialView'
import ProductionView from './views/ProductionView'

interface FailureState {
  kind: ApiErrorKind
  message: string
}

function tabs(response: PlanResponse): TabDefinition[] {
  const { plan } = response
  return [
    { id: 'production', label: 'Production', badge: `${plan.farm_comparison.length} farms` },
    { id: 'commercial', label: 'Commercial', badge: `${plan.kpis.at_risk_clients} at risk` },
    { id: 'allocations', label: 'Allocations', badge: `${plan.allocations.length} rows` },
  ]
}

export default function App() {
  const [status, setStatus] = useState<AppStatus>('idle')
  /** The last plan that loaded correctly. Kept on a server error, dropped on invalid input. */
  const [response, setResponse] = useState<PlanResponse | null>(null)
  const [loadedAt, setLoadedAt] = useState<Date | null>(null)
  const [issues, setIssues] = useState<ValidationIssue[]>([])
  const [failure, setFailure] = useState<FailureState | null>(null)
  const [message, setMessage] = useState('')
  const [selection, setSelection] = useState<Selection>(NO_SELECTION)
  const [activeTab, setActiveTab] = useState<TabId>('commercial')

  const load = useCallback(async () => {
    setStatus('loading')
    setMessage('Loading today’s data')
    try {
      const next = await loadSeedPlan()
      setResponse(next)
      setLoadedAt(new Date())
      setSelection(NO_SELECTION)
      setIssues([])
      setFailure(null)
      setStatus('ready')
      setMessage(
        `Plan ready. ${next.plan.kpis.export_volume_t} tonnes for export, ` +
          `${next.plan.kpis.at_risk_clients} clients at risk.`,
      )
    } catch (error) {
      const apiError =
        error instanceof ApiError
          ? error
          : new ApiError('server', 'Something went wrong on the server.')

      if (apiError.kind === 'validation') {
        // Never show a plan next to invalid input, not even an older one.
        setIssues(apiError.issues)
        setResponse(null)
        setLoadedAt(null)
        setFailure(null)
        setStatus('invalid')
        setMessage(`The workbook has ${apiError.issues.length} problems. Nothing was calculated.`)
      } else {
        setFailure({ kind: apiError.kind, message: apiError.message })
        setIssues([])
        setStatus('error')
        setMessage(apiError.message)
      }
    }
  }, [])

  /** One click on any id selects it and opens the view that explains it. */
  const handleSelect = useCallback((kind: EntityKind, id: string) => {
    setSelection((current) => withSelection(current, kind, id))
    setActiveTab(TAB_FOR_KIND[kind])
  }, [])

  const handleSetFilter = useCallback((kind: EntityKind, id: string | null) => {
    setSelection((current) => setFilter(current, kind, id))
  }, [])

  const clearFilters = useCallback(() => setSelection(NO_SELECTION), [])

  const loading = status === 'loading'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header
        status={status}
        source={response?.source ?? null}
        sourceFile={response?.source_file ?? null}
        loadedAt={loadedAt}
        errorCount={issues.length}
        onReload={load}
      />

      <main className="mx-auto max-w-[1400px] px-6 py-6">
        <p aria-live="polite" className="sr-only">
          {message}
        </p>

        <div className="space-y-6">
          {status === 'idle' ? <EmptyState onLoad={load} /> : null}

          {loading && !response ? <LoadingSkeleton /> : null}

          {status === 'invalid' ? (
            <ValidationErrorPanel issues={issues} onRetry={load} retrying={loading} />
          ) : null}

          {status === 'error' && failure ? (
            <ErrorBanner
              kind={failure.kind}
              message={failure.message}
              onRetry={load}
              retrying={loading}
              hasLastPlan={response !== null}
            />
          ) : null}

          {response && status !== 'invalid' ? (
            <>
              {status === 'error' ? (
                <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                  Last successful plan
                </p>
              ) : null}
              <DecisionSummary
                plan={response.plan}
                selection={selection}
                onSelect={handleSelect}
                stale={status === 'error'}
              />
              <WhatChanged plan={response.plan} selection={selection} onSelect={handleSelect} />
              <section aria-labelledby="detail-heading">
                <h2 id="detail-heading" className="text-lg font-semibold text-slate-900">
                  Follow the detail
                </h2>
                <div className="mt-2 mb-3">
                  <SelectionBar
                    selection={selection}
                    onSetFilter={handleSetFilter}
                    onClear={clearFilters}
                  />
                </div>
                <Tabs tabs={tabs(response)} active={activeTab} onChange={setActiveTab}>
                  {activeTab === 'production' ? (
                    <ProductionView
                      plan={response.plan}
                      selection={selection}
                      onSelect={handleSelect}
                    />
                  ) : null}
                  {activeTab === 'commercial' ? (
                    <CommercialView
                      plan={response.plan}
                      selection={selection}
                      onSelect={handleSelect}
                    />
                  ) : null}
                  {activeTab === 'allocations' ? (
                    <AllocationsView
                      plan={response.plan}
                      selection={selection}
                      onSelect={handleSelect}
                      onSetFilter={handleSetFilter}
                      onClearFilters={clearFilters}
                    />
                  ) : null}
                </Tabs>
              </section>
            </>
          ) : null}
        </div>
      </main>
    </div>
  )
}
