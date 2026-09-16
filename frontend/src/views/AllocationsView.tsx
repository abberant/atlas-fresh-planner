import { SEGMENTS, type PlanResult, type Segment } from '../api/types'
import { formatEur, formatNumber, formatTonnes, formatUpgrade } from '../lib/format'
import { isEmpty, type EntityKind, type Selection } from '../lib/selection'
import IdLink from '../components/IdLink'

interface AllocationsViewProps {
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
  onSetFilter: (kind: EntityKind, id: string | null) => void
  onClearFilters: () => void
}

const SELECT_CLASS =
  'rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900 ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-sky-700'

export default function AllocationsView({
  plan,
  selection,
  onSelect,
  onSetFilter,
  onClearFilters,
}: AllocationsViewProps) {
  const farmIds = plan.farm_comparison.map((farm) => farm.farm_id)
  const clientIds = plan.clients.map((client) => client.client_id)

  const rows = plan.allocations.filter(
    (row) =>
      (!selection.farmId || row.farm_id === selection.farmId) &&
      (!selection.clientId || row.client_id === selection.clientId) &&
      (!selection.segment || row.segment === selection.segment),
  )
  const residuals = plan.residuals.filter(
    (row) =>
      (!selection.farmId || row.farm_id === selection.farmId) &&
      (!selection.segment || row.segment === selection.segment),
  )

  const tonnes = rows.reduce((sum, row) => sum + row.tonnes, 0)
  const revenue = rows.reduce((sum, row) => sum + row.revenue_eur, 0)
  const localTonnes = residuals.reduce((sum, row) => sum + row.tonnes, 0)
  const localValue = residuals.reduce((sum, row) => sum + row.local_value_eur, 0)

  return (
    <section aria-labelledby="allocations-heading" className="pt-4">
      <h3 id="allocations-heading" className="text-base font-semibold text-slate-900">
        Every tonne, from farm to client
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        One row per farm, quality segment and client. Fruit with no export home is listed under the
        local market below.
      </p>

      <div className="mt-3 flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <div>
          <label htmlFor="filter-farm" className="block text-xs font-semibold text-slate-600">
            Farm
          </label>
          <select
            id="filter-farm"
            className={`mt-1 ${SELECT_CLASS}`}
            value={selection.farmId ?? ''}
            onChange={(event) => onSetFilter('farm', event.target.value || null)}
          >
            <option value="">All farms</option>
            {farmIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="filter-client" className="block text-xs font-semibold text-slate-600">
            Client
          </label>
          <select
            id="filter-client"
            className={`mt-1 ${SELECT_CLASS}`}
            value={selection.clientId ?? ''}
            onChange={(event) => onSetFilter('client', event.target.value || null)}
          >
            <option value="">All clients</option>
            {clientIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="filter-segment" className="block text-xs font-semibold text-slate-600">
            Quality segment
          </label>
          <select
            id="filter-segment"
            className={`mt-1 ${SELECT_CLASS}`}
            value={selection.segment ?? ''}
            onChange={(event) => onSetFilter('segment', (event.target.value as Segment) || null)}
          >
            <option value="">All segments</option>
            {SEGMENTS.map((segment) => (
              <option key={segment} value={segment}>
                Segment {segment}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={onClearFilters}
          disabled={isEmpty(selection)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 disabled:cursor-not-allowed disabled:text-slate-400"
        >
          Clear filters
        </button>

        <p className="ml-auto text-sm text-slate-600">
          Showing {rows.length} of {plan.allocations.length} rows
        </p>
      </div>

      <div className="mt-3 max-h-[30rem] overflow-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[54rem] border-collapse text-left text-sm">
          <caption className="sr-only">Export allocations from farms to clients</caption>
          <thead className="sticky top-0 z-10 bg-slate-100 text-slate-700">
            <tr>
              <th scope="col" className="px-3 py-2 font-semibold">Farm</th>
              <th scope="col" className="px-3 py-2 font-semibold">Segment</th>
              <th scope="col" className="px-3 py-2 font-semibold">Client</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Tonnes</th>
              <th scope="col" className="px-3 py-2 font-semibold">Quality upgrade</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Price (EUR/t)</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-600">
                  No export row matches these filters.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.row_id} className="border-t border-slate-200">
                  <td className="px-3 py-2">
                    <IdLink
                      kind="farm"
                      id={row.farm_id}
                      onSelect={onSelect}
                      active={selection.farmId === row.farm_id}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <IdLink
                      kind="segment"
                      id={row.segment}
                      onSelect={onSelect}
                      active={selection.segment === row.segment}
                    >
                      Segment {row.segment}
                    </IdLink>
                  </td>
                  <td className="px-3 py-2">
                    <IdLink
                      kind="client"
                      id={row.client_id}
                      onSelect={onSelect}
                      active={selection.clientId === row.client_id}
                    />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatTonnes(row.tonnes)}</td>
                  <td className="px-3 py-2 text-slate-700">{formatUpgrade(row.quality_upgrade)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatNumber(row.price_per_t)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatEur(row.revenue_eur)}</td>
                </tr>
              ))
            )}
          </tbody>
          <tfoot className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
            <tr>
              <td className="px-3 py-2" colSpan={3}>
                Export total{isEmpty(selection) ? '' : ' for these filters'}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">{formatTonnes(tonnes)}</td>
              <td className="px-3 py-2" />
              <td className="px-3 py-2" />
              <td className="px-3 py-2 text-right tabular-nums">{formatEur(revenue)}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <h4 className="mt-6 text-base font-semibold text-slate-900">Local market</h4>
      <p className="mt-1 text-sm text-slate-600">
        Fruit that was received but not exported. It is paid at the local ratio times the export
        reference price of its own segment.
      </p>

      <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[40rem] border-collapse text-left text-sm">
          <caption className="sr-only">Tonnes going to the local market with their value</caption>
          <thead className="bg-slate-100 text-slate-700">
            <tr>
              <th scope="col" className="px-3 py-2 font-semibold">Farm</th>
              <th scope="col" className="px-3 py-2 font-semibold">Segment</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Tonnes</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">
                Reference price (EUR/t)
              </th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Local value</th>
            </tr>
          </thead>
          <tbody>
            {residuals.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-slate-600">
                  {plan.residuals.length === 0
                    ? 'Every tonne received was exported today.'
                    : 'No local market row matches these filters.'}
                </td>
              </tr>
            ) : (
              residuals.map((row) => (
                <tr key={`${row.farm_id}-${row.segment}`} className="border-t border-slate-200">
                  <td className="px-3 py-2">
                    <IdLink
                      kind="farm"
                      id={row.farm_id}
                      onSelect={onSelect}
                      active={selection.farmId === row.farm_id}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <IdLink
                      kind="segment"
                      id={row.segment}
                      onSelect={onSelect}
                      active={selection.segment === row.segment}
                    >
                      Segment {row.segment}
                    </IdLink>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatTonnes(row.tonnes)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatNumber(row.reference_price_per_t)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatEur(row.local_value_eur)}</td>
                </tr>
              ))
            )}
          </tbody>
          <tfoot className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
            <tr>
              <td className="px-3 py-2" colSpan={2}>
                Local total{isEmpty(selection) ? '' : ' for these filters'}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">{formatTonnes(localTonnes)}</td>
              <td className="px-3 py-2" />
              <td className="px-3 py-2 text-right tabular-nums">{formatEur(localValue)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  )
}
