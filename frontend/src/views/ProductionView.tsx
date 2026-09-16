import { useEffect, useRef } from 'react'
import { SEGMENTS, type PlanResult } from '../api/types'
import { formatTonnes } from '../lib/format'
import type { EntityKind, Selection } from '../lib/selection'
import IdLink from '../components/IdLink'
import Variance from '../components/Variance'

interface ProductionViewProps {
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}

export default function ProductionView({ plan, selection, onSelect }: ProductionViewProps) {
  const selectedRow = useRef<HTMLTableRowElement | null>(null)

  useEffect(() => {
    selectedRow.current?.scrollIntoView({ block: 'nearest' })
  }, [selection.farmId])

  // Biggest shortfall first, so the farms that explain today's gap come to the top.
  const farms = [...plan.farm_comparison].sort(
    (a, b) => a.variance_total_t - b.variance_total_t || a.farm_id.localeCompare(b.farm_id),
  )

  return (
    <section aria-labelledby="production-heading" className="pt-4">
      <h3 id="production-heading" className="text-base font-semibold text-slate-900">
        Farms, expected against what arrived
      </h3>
      <p className="mt-1 text-sm text-slate-600">
        Sorted by the biggest shortfall against the daily plan. Farms with tonnes going to the local
        market are marked.
      </p>

      <div className="mt-3 max-h-[32rem] overflow-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[58rem] border-collapse text-left text-sm">
          <caption className="sr-only">
            Every farm with its expected capacity, what arrived, the gap, and the split by quality
            segment
          </caption>
          <thead className="sticky top-0 z-10 bg-slate-100 text-slate-700">
            <tr>
              <th scope="col" className="px-3 py-2 font-semibold">Farm</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Expected</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Arrived</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold">Gap</th>
              {SEGMENTS.map((segment) => (
                <th key={segment} scope="col" className="px-3 py-2 text-right font-semibold">
                  Segment {segment}
                </th>
              ))}
              <th scope="col" className="px-3 py-2 text-right font-semibold">To local market</th>
            </tr>
          </thead>
          <tbody>
            {farms.map((farm) => {
              const selected = selection.farmId === farm.farm_id
              return (
                <tr
                  key={farm.farm_id}
                  ref={selected ? selectedRow : null}
                  className={[
                    'border-t border-slate-200',
                    selected ? 'bg-sky-50 outline outline-2 -outline-offset-2 outline-sky-700' : '',
                  ].join(' ')}
                >
                  <td className="px-3 py-2">
                    <IdLink kind="farm" id={farm.farm_id} onSelect={onSelect} active={selected} />
                    <span className="block text-xs text-slate-600">{farm.farm_name}</span>
                    {selected ? <span className="sr-only"> (selected)</span> : null}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatTonnes(farm.expected_total_t)}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatTonnes(farm.actual_total_t)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <Variance value={farm.variance_total_t} />
                  </td>
                  {SEGMENTS.map((segment) => {
                    const cell = farm.segments[segment]
                    return (
                      <td key={segment} className="px-3 py-2 text-right">
                        <span className="tabular-nums">{formatTonnes(cell.actual_t)}</span>
                        <br />
                        <Variance value={cell.variance_t} small />
                      </td>
                    )
                  })}
                  <td className="px-3 py-2 text-right tabular-nums">
                    {farm.local_total_t > 0 ? (
                      <span className="rounded bg-rose-100 px-2 py-0.5 font-medium text-rose-900">
                        {formatTonnes(farm.local_total_t)}
                      </span>
                    ) : (
                      <span className="text-slate-400">&ndash;</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
            <tr>
              <td className="px-3 py-2">Total</td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatTonnes(plan.kpis.expected_plan_total_t)}
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatTonnes(plan.kpis.actual_received_t)}
              </td>
              <td className="px-3 py-2 text-right">
                <Variance value={plan.kpis.actual_received_t - plan.kpis.expected_plan_total_t} />
              </td>
              {plan.segment_comparison.map((row) => (
                <td key={row.segment} className="px-3 py-2 text-right">
                  <span className="tabular-nums">{formatTonnes(row.actual_t)}</span>
                  <br />
                  <Variance value={row.variance_t} small />
                </td>
              ))}
              <td className="px-3 py-2 text-right tabular-nums">
                {formatTonnes(plan.kpis.local_volume_t)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  )
}
