import { useEffect, useRef } from 'react'
import type { ClientResult, PlanResult } from '../api/types'
import { formatEur, formatNumber, formatTonnes } from '../lib/format'
import type { EntityKind, Selection } from '../lib/selection'
import { reasonInPlainWords } from '../lib/summary'
import IdLink from '../components/IdLink'
import StatusBadge from '../components/StatusBadge'

interface CommercialViewProps {
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}

function ruleAccepts(client: ClientResult): string {
  return client.mode === 'EXACT'
    ? `accepts ${client.requested_segment} only`
    : `accepts ${client.accepted_segments.join(' or ')}`
}

function ProgressBar({ allocated, demand }: { allocated: number; demand: number }) {
  const share = demand > 0 ? Math.min(1, allocated / demand) : 1
  const complete = allocated >= demand
  return (
    <div aria-hidden="true" className="mt-1 h-1.5 w-24 rounded-full bg-slate-200">
      <div
        className={`h-1.5 rounded-full ${complete ? 'bg-emerald-600' : 'bg-rose-600'}`}
        style={{ width: `${share * 100}%` }}
      />
    </div>
  )
}

export default function CommercialView({ plan, selection, onSelect }: CommercialViewProps) {
  const selectedRow = useRef<HTMLTableRowElement | null>(null)

  useEffect(() => {
    selectedRow.current?.scrollIntoView({ block: 'nearest' })
  }, [selection.clientId])

  return (
    <section aria-labelledby="commercial-heading" className="pt-4">
      <h3 id="commercial-heading" className="text-base font-semibold text-slate-900">
        Clients in the order they are served
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        The highest price is served first. Equal prices are broken by client id. Demand is a maximum,
        partial service is allowed.
      </p>

      <div className="mt-3 max-h-[32rem] overflow-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[58rem] border-collapse text-left text-sm">
          <caption className="sr-only">
            Every client with its quality rule, price, demand, what it received and why
          </caption>
          <thead className="sticky top-0 z-10 bg-slate-100 text-slate-700">
            <tr>
              <th scope="col" className="px-3 py-2 font-semibold">Order</th>
              <th scope="col" className="px-3 py-2 font-semibold">Client</th>
              <th scope="col" className="px-3 py-2 font-semibold">Quality rule</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Price (EUR/t)</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Demand</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Allocated</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Remaining</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Revenue</th>
              <th scope="col" className="px-3 py-2 font-semibold">Status</th>
              <th scope="col" className="px-3 py-2 font-semibold">Why</th>
            </tr>
          </thead>
          <tbody>
            {plan.clients.map((client) => {
              const selected = selection.clientId === client.client_id
              return (
                <tr
                  key={client.client_id}
                  ref={selected ? selectedRow : null}
                  className={[
                    'border-t border-slate-200',
                    selected ? 'bg-sky-50 outline outline-2 -outline-offset-2 outline-sky-700' : '',
                  ].join(' ')}
                >
                  <td className="px-3 py-2 tabular-nums text-slate-600">{client.processing_order}</td>
                  <td className="px-3 py-2">
                    <IdLink
                      kind="client"
                      id={client.client_id}
                      onSelect={onSelect}
                      active={selected}
                    />
                    <span className="block text-xs text-slate-600">{client.client_name}</span>
                    {selected ? <span className="sr-only"> (selected)</span> : null}
                  </td>
                  <td className="px-3 py-2">
                    <span className="whitespace-nowrap font-medium text-slate-800">
                      {client.mode} {client.requested_segment}
                    </span>
                    <span className="block text-xs text-slate-600">{ruleAccepts(client)}</span>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatNumber(client.price_per_t)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatTonnes(client.demand_t)}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatTonnes(client.allocated_t)}
                    <ProgressBar allocated={client.allocated_t} demand={client.demand_t} />
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {client.remaining_t > 0 ? formatTonnes(client.remaining_t) : '–'}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{formatEur(client.revenue_eur)}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={client.status} />
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {client.reason
                      ? reasonInPlainWords(
                          client.reason,
                          client.requested_segment,
                          plan.kpis.station_capacity_t,
                        )
                      : '–'}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
            <tr>
              <td className="px-3 py-2" colSpan={4}>
                Total
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatTonnes(plan.clients.reduce((sum, c) => sum + c.demand_t, 0))}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatTonnes(plan.kpis.export_volume_t)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatTonnes(plan.clients.reduce((sum, c) => sum + c.remaining_t, 0))}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatEur(plan.kpis.export_revenue_eur)}
              </td>
              <td className="px-3 py-2" colSpan={2}>
                {plan.kpis.at_risk_clients} at risk
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  )
}
