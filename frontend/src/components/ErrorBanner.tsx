import type { ApiErrorKind } from '../api/client'

interface ErrorBannerProps {
  kind: ApiErrorKind
  message: string
  onRetry: () => void
  retrying: boolean
  hasLastPlan: boolean
}

const TITLES: Partial<Record<ApiErrorKind, string>> = {
  network: 'The server could not be reached',
  timeout: 'The server took too long to answer',
  server: 'The server had a problem',
  bad_request: 'The request was not understood',
}

export default function ErrorBanner({ kind, message, onRetry, retrying, hasLastPlan }: ErrorBannerProps) {
  return (
    <section
      aria-labelledby="error-heading"
      className="rounded-lg border border-amber-300 bg-amber-50 p-5 shadow-sm"
    >
      <h2 id="error-heading" className="text-lg font-semibold text-amber-900">
        <span aria-hidden="true" className="mr-2">
          !
        </span>
        {TITLES[kind] ?? 'Something went wrong'}
      </h2>
      <p className="mt-2 text-amber-900">{message}</p>
      {hasLastPlan ? (
        <p className="mt-1 text-amber-900">
          The numbers below are the last plan that loaded correctly. They may be out of date.
        </p>
      ) : null}
      <button
        type="button"
        onClick={onRetry}
        disabled={retrying}
        className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        {retrying ? 'Trying…' : 'Try again'}
      </button>
    </section>
  )
}
