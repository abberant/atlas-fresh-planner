import type { FarmComparison, PlanResult, Segment, SegmentComparison } from '../api/types'
import { formatEur, formatPercent, formatSignedTonnes, formatTonnes, varianceMark } from '../lib/format'
import type { EntityKind, Selection } from '../lib/selection'
import { localReason } from '../lib/summary'
import IdLink from './IdLink'

const MAX_FARMS_SHOWN = 3

interface WhatChangedProps {
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}

interface Hit {
  clientId: string
  shortfallT: number
}

function farmsBelowPlan(farms: FarmComparison[], segment: Segment) {
  return farms
    .filter((farm) => farm.segments[segment].variance_t < 0)
    .sort((a, b) => a.segments[segment].variance_t - b.segments[segment].variance_t)
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="font-medium tabular-nums text-slate-900">{value}</dd>
    </div>
  )
}

function SegmentCard({
  row,
  hits,
  farms,
  localReason,
  selection,
  onSelect,
}: {
  row: SegmentComparison
  hits: Hit[]
  farms: FarmComparison[]
  localReason: string
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}) {
  const mark = varianceMark(row.variance_t)
  const below = farmsBelowPlan(farms, row.segment)
  const shown = below.slice(0, MAX_FARMS_SHOWN)
  const attention = hits.length > 0 || row.local_t > 0

  return (
    <article
      className={[
        'rounded-lg border bg-white p-4',
        attention ? 'border-rose-300 border-l-4 border-l-rose-600' : 'border-slate-200',
      ].join(' ')}
    >
      <h4 className="text-base font-semibold text-slate-900">
        <IdLink
          kind="segment"
          id={row.segment}
          onSelect={onSelect}
          active={selection.segment === row.segment}
        >
          Segment {row.segment}
        </IdLink>
      </h4>

      <p className="mt-1 text-sm font-medium text-slate-800">
        {formatSignedTonnes(row.variance_t)} <span aria-hidden="true">{mark.arrow}</span> {mark.label}
      </p>

      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-sm">
        <Figure label="Expected" value={formatTonnes(row.expected_t)} />
        <Figure label="Actual" value={formatTonnes(row.actual_t)} />
        <Figure label="Exported" value={formatTonnes(row.exported_t)} />
        <Figure label="To local market" value={formatTonnes(row.local_t)} />
      </dl>

      <div className="mt-3 border-t border-slate-200 pt-3 text-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Who it hits</p>
        {hits.length === 0 ? (
          <p className="mt-1 text-slate-600">
            No client is short on this quality today.
            {row.local_t > 0
              ? ` ${formatTonnes(row.local_t)} stay unexported because ${localReason}.`
              : ''}
          </p>
        ) : (
          <ul className="mt-1 space-y-0.5">
            {hits.map((hit) => (
              <li key={hit.clientId} className="text-slate-800">
                <IdLink
                  kind="client"
                  id={hit.clientId}
                  onSelect={onSelect}
                  active={selection.clientId === hit.clientId}
                />{' '}
                short {formatTonnes(hit.shortfallT)}
              </li>
            ))}
          </ul>
        )}
      </div>

      {shown.length > 0 ? (
        <div className="mt-3 text-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Farms below plan
          </p>
          <p className="mt-1 text-slate-800">
            {shown.map((farm, index) => (
              <span key={farm.farm_id}>
                {index > 0 ? ', ' : ''}
                <IdLink
                  kind="farm"
                  id={farm.farm_id}
                  onSelect={onSelect}
                  active={selection.farmId === farm.farm_id}
                />{' '}
                {formatSignedTonnes(farm.segments[row.segment].variance_t)}
              </span>
            ))}
            {below.length > shown.length ? (
              <span className="text-slate-500"> and {below.length - shown.length} more</span>
            ) : null}
          </p>
        </div>
      ) : null}
    </article>
  )
}

function CapacityCard({
  plan,
  selection,
  onSelect,
}: {
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
}) {
  const { kpis } = plan
  const full = kpis.export_volume_t >= kpis.station_capacity_t
  const hits = plan.risk_links.filter((link) => link.reason === 'STATION_CAPACITY_REACHED')
  const residualFarms = plan.residuals

  return (
    <article
      className={[
        'rounded-lg border bg-white p-4',
        hits.length > 0 ? 'border-rose-300 border-l-4 border-l-rose-600' : 'border-slate-200',
      ].join(' ')}
    >
      <h4 className="text-base font-semibold text-slate-900">Station capacity</h4>
      <p className="mt-1 text-sm font-medium text-slate-800">
        {formatTonnes(kpis.export_volume_t)} packed of {formatTonnes(kpis.station_capacity_t)} (
        {formatPercent(kpis.station_utilization)}
        {full ? ', full' : ', room to spare'})
      </p>

      <div className="mt-3 grid grid-cols-1 gap-4 border-t border-slate-200 pt-3 text-sm lg:grid-cols-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Who it hits</p>
          {hits.length === 0 ? (
            <p className="mt-1 text-slate-600">No client is short because of the station limit.</p>
          ) : (
            <ul className="mt-1 space-y-0.5">
              {hits.map((link) => (
                <li key={link.client_id} className="text-slate-800">
                  <IdLink
                    kind="client"
                    id={link.client_id}
                    onSelect={onSelect}
                    active={selection.clientId === link.client_id}
                  />{' '}
                  short {formatTonnes(link.shortfall_t)}, the station was already full
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            What stays unexported
          </p>
          {residualFarms.length === 0 ? (
            <p className="mt-1 text-slate-600">Every tonne received was exported.</p>
          ) : (
            <>
              <p className="mt-1 text-slate-800">
                {formatTonnes(kpis.local_volume_t)} go to the local market for{' '}
                {formatEur(kpis.local_value_eur)}, worth{' '}
                {formatEur(kpis.local_value_at_reference_eur)} at export reference price.
              </p>
              <p className="mt-1 text-slate-800">
                {residualFarms.map((row, index) => (
                  <span key={`${row.farm_id}-${row.segment}`}>
                    {index > 0 ? ', ' : ''}
                    <IdLink
                      kind="farm"
                      id={row.farm_id}
                      onSelect={onSelect}
                      active={selection.farmId === row.farm_id}
                    />{' '}
                    {formatTonnes(row.tonnes)} of {row.segment}
                  </span>
                ))}
              </p>
            </>
          )}
        </div>
      </div>
    </article>
  )
}

export default function WhatChanged({ plan, selection, onSelect }: WhatChangedProps) {
  const reasonForLocal = localReason(plan)
  const hitsBySegment = new Map<Segment, Hit[]>()
  for (const link of plan.risk_links) {
    for (const segment of link.segments_involved) {
      const hits = hitsBySegment.get(segment) ?? []
      // A client short on capacity is explained by the capacity card, not by quality.
      if (link.reason === 'INSUFFICIENT_COMPATIBLE_SEGMENT') {
        hits.push({ clientId: link.client_id, shortfallT: link.shortfall_t })
      }
      hitsBySegment.set(segment, hits)
    }
  }

  return (
    <section aria-labelledby="what-changed-heading">
      <h2 id="what-changed-heading" className="text-lg font-semibold text-slate-900">
        What changed and who it hits
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        Each quality segment against plan, and the clients that feel the gap.
      </p>

      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {plan.segment_comparison.map((row) => (
          <SegmentCard
            key={row.segment}
            row={row}
            hits={hitsBySegment.get(row.segment) ?? []}
            farms={plan.farm_comparison}
            localReason={reasonForLocal}
            selection={selection}
            onSelect={onSelect}
          />
        ))}
      </div>

      <div className="mt-3">
        <CapacityCard plan={plan} selection={selection} onSelect={onSelect} />
      </div>
    </section>
  )
}
