import { useCallback, useState } from 'react'
import { ApiError, loadSeedPlan, type ApiErrorKind } from './api/client'
import type { PlanResponse, ValidationIssue } from './api/types'
import DecisionSummary from './components/DecisionSummary'
import EmptyState from './components/EmptyState'
import ErrorBanner from './components/ErrorBanner'
import Header, { type AppStatus } from './components/Header'
import LoadingSkeleton from './components/LoadingSkeleton'
import ValidationErrorPanel from './components/ValidationErrorPanel'

interface FailureState {
  kind: ApiErrorKind
  message: string
}

export default function App() {
  const [status, setStatus] = useState<AppStatus>('idle')
  /** The last plan that loaded correctly. Kept on a server error, dropped on invalid input. */
  const [response, setResponse] = useState<PlanResponse | null>(null)
  const [issues, setIssues] = useState<ValidationIssue[]>([])
  const [failure, setFailure] = useState<FailureState | null>(null)
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    setStatus('loading')
    setMessage('Loading today’s data')
    try {
      const next = await loadSeedPlan()
      setResponse(next)
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

  const loading = status === 'loading'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <Header status={status} source={response?.source ?? null} errorCount={issues.length} onReload={load} />

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
              <DecisionSummary plan={response.plan} stale={status === 'error'} />
              <section
                aria-labelledby="next-heading"
                className="rounded-lg border border-dashed border-slate-300 bg-white p-5 text-slate-600"
              >
                <h2 id="next-heading" className="text-base font-semibold text-slate-800">
                  Detail views
                </h2>
                <p className="mt-1 text-sm">
                  The segment impact cards and the Production, Commercial and Allocations tabs are the
                  next step.
                </p>
              </section>
            </>
          ) : null}
        </div>
      </main>
    </div>
  )
}
