import type { PlanResult } from '../api/types'
import { formatEur, formatPercent, formatSignedTonnes, formatTonnes, varianceMark } from '../lib/format'
import type { EntityKind, Selection } from '../lib/selection'
import { buildSummarySentence, groupAtRiskClients, worstSegment } from '../lib/summary'
import IdLink from './IdLink'
import KpiCard from './KpiCard'

interface DecisionSummaryProps {
  plan: PlanResult
  selection: Selection
  onSelect: (kind: EntityKind, id: string) => void
  stale?: boolean
}

export default function DecisionSummary({ plan, selection, onSelect, stale = false }: DecisionSummaryProps) {
  const { kpis } = plan
  const variance = kpis.actual_received_t - kpis.expected_plan_total_t
  const mark = varianceMark(variance)
  const riskGroups = groupAtRiskClients(plan)
  const worst = worstSegment(plan)

  const riskDetail =
    riskGroups.length === 0 ? (
      'Every client is fully served'
    ) : (
      <ul className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {riskGroups.map((group, index) => (
          <li key={group.reason}>
            {group.clientIds.map((clientId, position) => (
              <span key={clientId}>
                {position > 0 ? ', ' : ''}
                <IdLink
                  kind="client"
                  id={clientId}
                  onSelect={onSelect}
                  active={selection.clientId === clientId}
                />
              </span>
            ))}{' '}
            {group.label}
            {index < riskGroups.length - 1 ? (
              <span aria-hidden="true" className="ml-2 text-slate-400">
                &middot;
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    )

  return (
    <section aria-labelledby="decision-summary-heading" className={stale ? 'opacity-75' : undefined}>
      <h2 id="decision-summary-heading" className="text-lg font-semibold text-slate-900">
        Today at a glance
      </h2>

      <p className="mt-2 max-w-5xl rounded-lg bg-slate-100 p-4 text-lg leading-relaxed text-slate-900">
        {buildSummarySentence(plan)}
      </p>

      <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-slate-700">
        Needs attention
      </h3>
      <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard
          label="Clients at risk"
          value={`${kpis.at_risk_clients} of ${plan.clients.length}`}
          detail={riskDetail}
          tone={kpis.at_risk_clients > 0 ? 'attention' : 'neutral'}
        />
        <KpiCard
          label="Going local"
          value={formatTonnes(kpis.local_volume_t)}
          detail={
            <>
              <p>worth {formatEur(kpis.local_value_eur)}</p>
              <p className="text-slate-600">
                {formatEur(kpis.local_value_at_reference_eur)} at export reference price
              </p>
            </>
          }
          tone={kpis.local_volume_t > 0 ? 'attention' : 'neutral'}
        />
        <KpiCard
          label="Planned vs actual"
          value={`${formatTonnes(kpis.actual_received_t)} of ${formatTonnes(kpis.expected_plan_total_t)}`}
          detail={
            <>
              <p>
                {formatSignedTonnes(variance)} <span aria-hidden="true">{mark.arrow}</span> {mark.label}
              </p>
              {worst ? (
                <p className="text-slate-600">
                  Biggest gap{' '}
                  <IdLink
                    kind="segment"
                    id={worst.segment}
                    onSelect={onSelect}
                    active={selection.segment === worst.segment}
                  >
                    Segment {worst.segment}
                  </IdLink>
                  : {formatSignedTonnes(worst.variance_t)}
                </p>
              ) : null}
            </>
          }
        />
      </div>

      <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-slate-500">
        Throughput and value
      </h3>
      <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <KpiCard
          size="support"
          label="Station use"
          value={`${formatTonnes(kpis.export_volume_t, false)} / ${formatTonnes(kpis.station_capacity_t)}`}
          detail={
            kpis.export_volume_t >= kpis.station_capacity_t
              ? `${formatPercent(kpis.station_utilization)}, the station is full`
              : `${formatPercent(kpis.station_utilization)} of capacity used`
          }
        />
        <KpiCard
          size="support"
          label="Export rate"
          value={formatPercent(kpis.export_rate)}
          detail={`${formatTonnes(kpis.export_volume_t)} exported of ${formatTonnes(
            kpis.actual_received_t,
          )} received`}
        />
        <KpiCard
          size="support"
          label="Value"
          value={formatEur(kpis.total_value_eur)}
          detail={`export ${formatEur(kpis.export_revenue_eur)} + local ${formatEur(kpis.local_value_eur)}`}
        />
      </div>
    </section>
  )
}
