interface EmptyStateProps {
  onLoad: () => void
}

export default function EmptyState({ onLoad }: EmptyStateProps) {
  return (
    <section
      aria-labelledby="empty-heading"
      className="mx-auto max-w-2xl rounded-lg border border-slate-200 bg-white p-10 text-center shadow-sm"
    >
      <h2 id="empty-heading" className="text-xl font-semibold text-slate-900">
        No plan loaded yet
      </h2>
      <p className="mx-auto mt-2 max-w-md text-slate-600">
        Load today&rsquo;s farm receipts and client program to see what can be exported, who is short
        and what goes to the local market.
      </p>
      <button
        type="button"
        onClick={onLoad}
        className="mt-6 rounded-md bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
      >
        Load today&rsquo;s data
      </button>
    </section>
  )
}
