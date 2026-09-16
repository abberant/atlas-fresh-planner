/** Shown while the plan is being built. Same shape as the real summary. */
export default function LoadingSkeleton() {
  return (
    <section aria-hidden="true">
      <div className="h-6 w-40 animate-pulse rounded bg-slate-200" />
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 7 }, (_, index) => (
          <div
            key={index}
            className={[
              'rounded-lg border border-slate-200 border-l-4 border-l-slate-200 bg-white p-4 shadow-sm',
              index === 6 ? 'sm:col-span-2 lg:col-span-3 xl:col-span-2' : '',
            ].join(' ')}
          >
            <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
            <div className="mt-3 h-7 w-32 animate-pulse rounded bg-slate-200" />
            <div className="mt-2 h-3 w-40 animate-pulse rounded bg-slate-100" />
          </div>
        ))}
      </div>
      <div className="mt-4 h-16 max-w-4xl animate-pulse rounded-lg bg-slate-100" />
    </section>
  )
}
