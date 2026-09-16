import type { ValidationIssue } from '../api/types'

interface ValidationErrorPanelProps {
  issues: ValidationIssue[]
  onRetry: () => void
  retrying: boolean
}

function place(issue: ValidationIssue): string {
  const parts = [issue.sheet]
  if (issue.row !== null) parts.push(`row ${issue.row}`)
  if (issue.entity_id) parts.push(issue.entity_id)
  return parts.join(' · ')
}

export default function ValidationErrorPanel({ issues, onRetry, retrying }: ValidationErrorPanelProps) {
  return (
    <section
      aria-labelledby="validation-heading"
      className="rounded-lg border border-rose-200 bg-white shadow-sm"
    >
      <div className="border-b border-rose-200 bg-rose-50 p-5">
        <h2 id="validation-heading" className="text-xl font-semibold text-rose-900">
          <span aria-hidden="true" className="mr-2">
            &#10007;
          </span>
          The workbook has {issues.length} {issues.length === 1 ? 'problem' : 'problems'}. Nothing was
          calculated.
        </h2>
        <p className="mt-2 text-rose-900">
          Fix the cells below in the input file, then load the data again. No plan is shown while the
          input is invalid.
        </p>
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {retrying ? 'Loading…' : 'Reload today’s data'}
        </button>
      </div>

      <div className="max-h-[28rem] overflow-y-auto">
        <table className="w-full border-collapse text-left text-sm">
          <caption className="sr-only">Every problem found in the workbook</caption>
          <thead className="sticky top-0 bg-slate-100 text-slate-700">
            <tr>
              <th scope="col" className="px-5 py-2 font-semibold">
                Where
              </th>
              <th scope="col" className="px-5 py-2 font-semibold">
                Problem
              </th>
              <th scope="col" className="px-5 py-2 font-semibold">
                What to fix
              </th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, index) => (
              <tr key={`${issue.code}-${index}`} className="border-t border-slate-200 align-top">
                <td className="whitespace-nowrap px-5 py-2 font-medium text-slate-900">{place(issue)}</td>
                <td className="whitespace-nowrap px-5 py-2 font-mono text-xs text-slate-700">
                  {issue.code}
                </td>
                <td className="px-5 py-2 text-slate-800">{issue.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
