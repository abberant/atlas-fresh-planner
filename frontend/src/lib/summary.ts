/**
 * The plain sentence under the decision summary, built from the plan.
 * No wording is stored: every number and every name comes from the data.
 */

import type { PlanResult, Segment, SegmentComparison, ShortageReason } from '../api/types'
import { formatTonnes, joinWithAnd } from './format'

/** Why fruit could not be exported: the station filled up, or no client could take it. */
export function localReason(plan: PlanResult): string {
  const { kpis } = plan
  return kpis.export_volume_t >= kpis.station_capacity_t
    ? `the station is full at ${formatTonnes(kpis.station_capacity_t)}`
    : 'no client could take that quality today'
}

export function buildSummarySentence(plan: PlanResult): string {
  const { kpis } = plan
  const parts: string[] = []

  parts.push(
    `${formatTonnes(kpis.actual_received_t)} arrived versus ` +
      `${formatTonnes(kpis.expected_plan_total_t)} planned.`,
  )

  const risk =
    kpis.at_risk_clients === 0
      ? 'Every client is fully served'
      : `${kpis.at_risk_clients} ${kpis.at_risk_clients === 1 ? 'client is' : 'clients are'} short`

  if (kpis.local_volume_t > 0) {
    const segments = plan.segment_comparison
      .filter((row) => row.local_t > 0)
      .map((row) => `Segment ${row.segment}`)
    parts.push(
      `${risk} and ${formatTonnes(kpis.local_volume_t)} of ${joinWithAnd(segments)} ` +
        `go to the local market because ${localReason(plan)}.`,
    )
  } else {
    parts.push(`${risk} and nothing goes to the local market.`)
  }

  return parts.join(' ')
}

/** At risk client ids grouped by the reason they are short. */
export interface RiskGroup {
  reason: ShortageReason
  label: string
  clientIds: string[]
}

export function groupAtRiskClients(plan: PlanResult): RiskGroup[] {
  const order: { reason: ShortageReason; label: string }[] = [
    { reason: 'INSUFFICIENT_COMPATIBLE_SEGMENT', label: 'short on quality' },
    { reason: 'STATION_CAPACITY_REACHED', label: 'station full' },
  ]
  return order
    .map(({ reason, label }) => ({
      reason,
      label,
      clientIds: plan.clients.filter((client) => client.reason === reason).map((c) => c.client_id),
    }))
    .filter((group) => group.clientIds.length > 0)
}

/** The segment that missed its plan by the most tonnes today. Null when nothing is below plan. */
export function worstSegment(plan: PlanResult): SegmentComparison | null {
  const below = plan.segment_comparison.filter((row) => row.variance_t < 0)
  if (below.length === 0) return null
  return below.reduce((worst, row) => (row.variance_t < worst.variance_t ? row : worst))
}

/** Plain words for a shortage reason, used in the Commercial table. */
export function reasonInPlainWords(
  reason: ShortageReason,
  requestedSegment: Segment,
  capacityT: number,
): string {
  return reason === 'STATION_CAPACITY_REACHED'
    ? `Station full at ${formatTonnes(capacityT)}`
    : `Not enough Segment ${requestedSegment}`
}
