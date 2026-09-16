/**
 * Types that mirror the Pydantic models of the server.
 * Keep this file in step with backend/app/domain/models.py.
 */

export type Segment = 'A' | 'B' | 'C' | 'D'
export type AcceptanceMode = 'EXACT' | 'MINIMUM'
export type ClientStatus = 'COMPLETE' | 'PARTIAL' | 'UNSERVED'
export type ShortageReason = 'STATION_CAPACITY_REACHED' | 'INSUFFICIENT_COMPATIBLE_SEGMENT'

export const SEGMENTS: readonly Segment[] = ['A', 'B', 'C', 'D']

export interface ValidationIssue {
  code: string
  sheet: string
  row: number | null
  entity_id: string | null
  field: string | null
  message: string
}

export interface Farm {
  farm_id: string
  farm_name: string
  row: number
  expected_daily_capacity_t: number
  expected_mix: Record<Segment, number>
  actual_t: Record<Segment, number>
}

export interface Client {
  client_id: string
  client_name: string
  row: number
  acceptance_mode: AcceptanceMode
  requested_segment: Segment
  demand_t: number
  export_price_per_t_eur: number
}

export interface Station {
  station_id: string
  export_conditioning_capacity_t: number
  local_market_ratio: number
}

export interface ReferencePrice {
  segment: Segment
  reference_export_price_per_t_eur: number
}

export interface SourcePayload {
  farms: Farm[]
  clients: Client[]
  station: Station
  reference_prices: ReferencePrice[]
}

export interface Kpis {
  expected_plan_total_t: number
  actual_received_t: number
  station_capacity_t: number
  export_volume_t: number
  local_volume_t: number
  /** Null when nothing was received today, shown as "n/a". */
  export_rate: number | null
  station_utilization: number | null
  export_revenue_eur: number
  local_value_eur: number
  total_value_eur: number
  at_risk_clients: number
  local_value_at_reference_eur: number
  value_lost_to_local_eur: number
}

export interface SegmentComparison {
  segment: Segment
  expected_t: number
  actual_t: number
  variance_t: number
  exported_t: number
  local_t: number
}

export interface FarmSegmentComparison {
  expected_t: number
  actual_t: number
  variance_t: number
  exported_t: number
  local_t: number
}

export interface FarmComparison {
  farm_id: string
  farm_name: string
  expected_total_t: number
  actual_total_t: number
  variance_total_t: number
  exported_total_t: number
  local_total_t: number
  segments: Record<Segment, FarmSegmentComparison>
}

export interface ClientResult {
  client_id: string
  client_name: string
  processing_order: number
  mode: AcceptanceMode
  requested_segment: Segment
  accepted_segments: Segment[]
  price_per_t: number
  demand_t: number
  allocated_t: number
  remaining_t: number
  revenue_eur: number
  status: ClientStatus
  reason: ShortageReason | null
}

export interface AllocationRow {
  row_id: number
  processing_order: number
  farm_id: string
  segment: Segment
  client_id: string
  tonnes: number
  quality_upgrade: number
  price_per_t: number
  revenue_eur: number
}

export interface ResidualRow {
  farm_id: string
  segment: Segment
  tonnes: number
  reference_price_per_t: number
  local_value_eur: number
}

export interface FarmSegmentVariance {
  farm_id: string
  segment: Segment
  variance_t: number
}

export interface RiskLink {
  client_id: string
  reason: ShortageReason
  shortfall_t: number
  segments_involved: Segment[]
  farms_below_plan: FarmSegmentVariance[]
  served_before: string[]
}

export interface Invariant {
  name: string
  passed: boolean
  detail: string
}

export interface PlanResult {
  kpis: Kpis
  segment_comparison: SegmentComparison[]
  farm_comparison: FarmComparison[]
  clients: ClientResult[]
  allocations: AllocationRow[]
  residuals: ResidualRow[]
  risk_links: RiskLink[]
  invariants: Invariant[]
}

export interface PlanResponse {
  plan_id: string
  /** Name of the file today's numbers came from. */
  source_file: string
  source: SourcePayload
  plan: PlanResult
}

export interface Health {
  status: string
  ai_provider: 'none' | 'anthropic' | 'ollama'
  ai_configured: boolean
}
