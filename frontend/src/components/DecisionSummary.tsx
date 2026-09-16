import type { PlanResult } from '../api/types'
import { formatEur, formatPercent, formatSignedTonnes, formatTonnes, varianceMark } from '../lib/format'
import { buildSummarySentence, countReasons } from '../lib/summary'
import KpiCard from './KpiCard'

interface DecisionSummaryProps {
  plan: PlanResult
  stale?: boolean
}

export default function DecisionSummary({ plan, stale = false }: DecisionSummaryProps) {
  const { kpis } = plan
  const variance = kpis.actual_received_t - kpis.expected_plan_total_t
  const mark = varianceMark(variance)
  const stationFull = kpis.export_volume_t >= kpis.station_capacity_t
  const reasons = countReasons(plan)

  const riskDetail =
    kpis.at_risk_clients === 0
      ? 'Every client is fully served'
      : [
          reasons.INSUFFICIENT_COMPATIBLE_SEGMENT > 0
            ? `${reasons.INSUFFICIENT_COMPATIBLE_SEGMENT} short on quality`
            : null,
          reasons.STATION_CAPACITY_REACHED > 0
            ? `${reasons.STATION_CAPACITY_REACHED} short on station capacity`
            : null,
        ]
          .filter(Boolean)
          .join(', ')

  return (
    <section aria-labelledby="decision-summary-heading" className={stale ? 'opacity-75' : undefined}>
      <h2 id="decision-summary-heading" className="text-lg font-semibold text-slate-900">
        Today at a glance
      </h2>

      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <KpiCard
          label="Planned vs actual"
          value={`${formatTonnes(kpis.actual_received_t)} of ${formatTonnes(kpis.expected_plan_total_t)}`}
          detail={`${formatSignedTonnes(variance)} ${mark.arrow} ${mark.label}`}
          tone={variance < 0 ? 'warn' : 'neutral'}
        />
        <KpiCard
          label="Station use"
          value={`${formatTonnes(kpis.export_volume_t, false)} / ${formatTonnes(kpis.station_capacity_t)}`}
          detail={
            stationFull
              ? `${formatPercent(kpis.station_utilization)}, the station is full`
              : `${formatPercent(kpis.station_utilization)} of capacity used`
          }
          tone={stationFull ? 'warn' : 'good'}
        />
        <KpiCard
          label="Export rate"
          value={formatPercent(kpis.export_rate)}
          detail={`${formatTonnes(kpis.export_volume_t)} exported of ${formatTonnes(kpis.actual_received_t)} received`}
        />
        <KpiCard
          label="Going local"
          value={formatTonnes(kpis.local_volume_t)}
          detail={`worth ${formatEur(kpis.local_value_eur)} instead of ${formatEur(
            kpis.local_value_at_reference_eur,
          )} at export reference price`}
          tone={kpis.local_volume_t > 0 ? 'risk' : 'good'}
        />
        <KpiCard
          label="Export revenue"
          value={formatEur(kpis.export_revenue_eur)}
          detail={`from ${formatTonnes(kpis.export_volume_t)} sent to clients`}
        />
        <KpiCard
          label="Total value"
          value={formatEur(kpis.total_value_eur)}
          detail={`export ${formatEur(kpis.export_revenue_eur)} plus local ${formatEur(kpis.local_value_eur)}`}
        />
        <KpiCard
          label="Clients at risk"
          value={`${kpis.at_risk_clients} of ${plan.clients.length}`}
          detail={riskDetail}
          tone={kpis.at_risk_clients > 0 ? 'risk' : 'good'}
          wide
        />
      </div>

      <p className="mt-4 max-w-4xl rounded-lg bg-slate-100 p-4 text-base leading-relaxed text-slate-800">
        {buildSummarySentence(plan)}
      </p>
    </section>
  )
}
