import { useCallback, useState, type FormEvent } from 'react'
import { ApiError, askAssistant } from '../api/client'
import type { AssistantResponse, Citation, PlanResult, QuestionId } from '../api/types'
import { formatTonnes } from '../lib/format'
import type { EntityKind, Selection } from '../lib/selection'
import IdLink from '../components/IdLink'

interface AssistantPanelProps {
  planId: string
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}

interface Preset {
  id: QuestionId
  label: string
}

/** Question labels are built from today's plan, never hard coded. */
function presets(plan: PlanResult): Preset[] {
  return [
    {
      id: 'at_risk_clients',
      label: `Which ${plan.kpis.at_risk_clients} clients are at risk and why?`,
    },
    { id: 'segment_gaps', label: 'Which farm and segment gaps matter most today?' },
    {
      id: 'local_residual',
      label:
        `Why are ${formatTonnes(plan.kpis.local_volume_t)} going to the local market ` +
        'and what are they worth?',
    },
  ]
}

const ERROR_TITLE: Record<string, string> = {
  TIMEOUT: 'The AI provider did not answer (timeout). No AI answer is shown.',
  PROVIDER_ERROR: 'The AI provider could not be reached. No AI answer is shown.',
  INVALID_OUTPUT:
    'The AI answer was rejected because it mentioned data that is not in today’s plan.',
}

function Citations({
  citations,
  selection,
  onSelect,
}: {
  citations: Citation[]
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}) {
  if (citations.length === 0) return null
  const active = (citation: Citation) =>
    citation.type === 'farm'
      ? selection.farmId === citation.id
      : citation.type === 'client'
        ? selection.clientId === citation.id
        : selection.segment === citation.id

  return (
    <p className="mt-3 text-sm text-slate-600">
      <span className="font-semibold">Based on </span>
      {citations.map((citation, index) => (
        <span key={`${citation.type}-${citation.id}`}>
          {index > 0 ? ', ' : ''}
          <IdLink
            kind={citation.type}
            id={citation.id}
            onSelect={onSelect}
            active={active(citation)}
          >
            {citation.type === 'segment' ? `Segment ${citation.id}` : citation.id}
          </IdLink>
        </span>
      ))}
    </p>
  )
}

export default function AssistantPanel({ planId, plan, selection, onSelect }: AssistantPanelProps) {
  const [open, setOpen] = useState(false)
  const [asking, setAsking] = useState(false)
  const [result, setResult] = useState<AssistantResponse | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [text, setText] = useState('')
  const [showFallback, setShowFallback] = useState(false)

  const run = useCallback(
    async (question: { questionId: QuestionId } | { questionText: string }) => {
      setAsking(true)
      setFailure(null)
      setShowFallback(false)
      try {
        setResult(await askAssistant(planId, question))
      } catch (error) {
        setResult(null)
        setFailure(
          error instanceof ApiError
            ? error.message
            : 'The assistant could not be reached. Please try again.',
        )
      } finally {
        setAsking(false)
      }
    },
    [planId],
  )

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const question = text.trim()
    if (question) void run({ questionText: question })
  }

  const isAi = result?.mode === 'ai'
  const isSummary = result?.mode === 'deterministic_summary'
  const isUnavailable = result?.mode === 'unavailable'
  const isError = result?.mode === 'error'

  return (
    <section
      aria-labelledby="assistant-heading"
      className="rounded-lg border border-slate-200 bg-white"
    >
      <div className="flex items-center gap-2 border-b border-slate-200 p-4">
        <h2 id="assistant-heading" className="text-base font-semibold text-slate-900">
          Ask about today&rsquo;s plan
        </h2>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-controls="assistant-body"
          className="ml-auto rounded-md border border-slate-300 px-3 py-1 text-sm font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 xl:hidden"
        >
          {open ? 'Hide' : 'Show'}
        </button>
      </div>

      <div id="assistant-body" className={`${open ? 'block' : 'hidden'} p-4 xl:block`}>
        <p className="text-sm text-slate-600">
          The assistant only explains the plan above. It never changes it and never
          calculates a number.
        </p>

        <ul className="mt-3 space-y-2">
          {presets(plan).map((preset) => (
            <li key={preset.id}>
              <button
                type="button"
                onClick={() => void run({ questionId: preset.id })}
                disabled={asking}
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-left text-sm font-medium text-slate-800 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:text-slate-400"
              >
                {preset.label}
              </button>
            </li>
          ))}
        </ul>

        <form onSubmit={submit} className="mt-3">
          <label htmlFor="assistant-question" className="block text-sm font-semibold text-slate-700">
            Or ask in your own words
          </label>
          <div className="mt-1 flex gap-2">
            <input
              id="assistant-question"
              type="text"
              value={text}
              maxLength={500}
              onChange={(event) => setText(event.target.value)}
              placeholder="Why is C09 short?"
              className="min-w-0 flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-sky-700"
            />
            <button
              type="submit"
              disabled={asking || text.trim().length === 0}
              className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {asking ? 'Asking…' : 'Ask'}
            </button>
          </div>
        </form>

        <div aria-live="polite" className="mt-4">
          {asking ? <p className="text-sm text-slate-600">Asking…</p> : null}

          {failure ? (
            <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              {failure}
            </div>
          ) : null}

          {result && !asking ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              {isAi ? (
                <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                  AI answer, checked against the plan
                </p>
              ) : null}

              {isSummary ? (
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                  Summary from the planning engine, no AI
                </p>
              ) : null}

              {isSummary && result.error_code === 'NO_KEY' ? (
                <p className="mt-1 text-xs text-slate-600">
                  AI is not configured, so no model was called. See the README to enable
                  Ollama or an API key.
                </p>
              ) : null}

              {isError ? (
                <p className="text-sm font-medium text-amber-900">
                  {ERROR_TITLE[result.error_code ?? ''] ?? 'The AI answer could not be shown.'}
                </p>
              ) : null}

              {isUnavailable || isAi || isSummary ? (
                <p className={`text-sm leading-relaxed text-slate-900 ${isAi || isSummary ? 'mt-2' : ''}`}>
                  {result.answer}
                </p>
              ) : null}

              {isAi || isSummary ? (
                <Citations
                  citations={result.citations}
                  selection={selection}
                  onSelect={onSelect}
                />
              ) : null}

              {isError && result.fallback_answer ? (
                showFallback ? (
                  <div className="mt-3 border-t border-slate-200 pt-3">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Summary from the planning engine, no AI
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-900">
                      {result.fallback_answer}
                    </p>
                    <Citations
                      citations={result.fallback_citations}
                      selection={selection}
                      onSelect={onSelect}
                    />
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setShowFallback(true)}
                    className="mt-3 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
                  >
                    Show the summary from the planning engine
                  </button>
                )
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
