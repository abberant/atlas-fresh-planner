/** Shown while the plan is being built. Same shape as the real summary. */
export default function LoadingSkeleton() {
  return (
    <section aria-hidden="true">
      <div className="h-6 w-40 animate-pulse rounded bg-slate-200" />
      <div className="mt-2 h-20 max-w-5xl animate-pulse rounded-lg bg-slate-100" />
      {[0, 1].map((row) => (
        <div key={row}>
          <div className="mt-5 h-4 w-36 animate-pulse rounded bg-slate-200" />
          <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {[0, 1, 2].map((card) => (
              <div key={card} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
                <div className={`mt-3 animate-pulse rounded bg-slate-200 ${row === 0 ? 'h-8 w-36' : 'h-6 w-28'}`} />
                <div className="mt-2 h-3 w-40 animate-pulse rounded bg-slate-100" />
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  )
}
