/**
 * The plain sentence under the decision summary, built from the plan.
 * No wording is stored: every number and every name comes from the data.
 */

import type { PlanResult, ShortageReason } from '../api/types'
import { formatEur, formatTonnes, joinWithAnd } from './format'

export function buildSummarySentence(plan: PlanResult): string {
  const { kpis } = plan
  const parts: string[] = []

  parts.push(
    `${formatTonnes(kpis.actual_received_t)} arrived versus ` +
      `${formatTonnes(kpis.expected_plan_total_t)} planned.`,
  )

  if (kpis.export_volume_t >= kpis.station_capacity_t) {
    parts.push(`The station is full at ${formatTonnes(kpis.station_capacity_t)}.`)
  } else {
    parts.push(
      `The station packed ${formatTonnes(kpis.export_volume_t)} of ` +
        `${formatTonnes(kpis.station_capacity_t)}.`,
    )
  }

  const localSegments = plan.segment_comparison
    .filter((row) => row.local_t > 0)
    .map((row) => `Segment ${row.segment}`)

  const risk =
    kpis.at_risk_clients === 0
      ? 'Every client is fully served'
      : `${kpis.at_risk_clients} ${kpis.at_risk_clients === 1 ? 'client is' : 'clients are'} short`

  if (kpis.local_volume_t > 0) {
    parts.push(
      `${risk} and ${formatTonnes(kpis.local_volume_t)} of ${joinWithAnd(localSegments)} ` +
        `go to the local market for ${formatEur(kpis.local_value_eur)}.`,
    )
  } else {
    parts.push(`${risk} and nothing goes to the local market.`)
  }

  return parts.join(' ')
}

/** How many clients at risk are short on quality, and how many on station capacity. */
export function countReasons(plan: PlanResult): Record<ShortageReason, number> {
  const counts: Record<ShortageReason, number> = {
    INSUFFICIENT_COMPATIBLE_SEGMENT: 0,
    STATION_CAPACITY_REACHED: 0,
  }
  for (const client of plan.clients) {
    if (client.reason) counts[client.reason] += 1
  }
  return counts
}

/** Short plain words for a shortage reason. */
export function reasonLabel(reason: ShortageReason, segments: string): string {
  return reason === 'STATION_CAPACITY_REACHED'
    ? 'Station full'
    : `Not enough ${segments}`
}
