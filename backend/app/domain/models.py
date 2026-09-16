"""Domain models for the parsed workbook (source) and for validation errors.

Money, ratios and expected tonnes are kept as Decimal so arithmetic stays exact.
They are serialised as plain JSON numbers for the client.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.domain.segments import AcceptanceMode, Segment

# Decimal keeps exact arithmetic on the server and becomes a normal number in JSON.
Dec = Annotated[
    Decimal,
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]


class Frozen(BaseModel):
    """Source models never change after parsing."""

    model_config = ConfigDict(frozen=True)


class ValidationIssue(Frozen):
    """One rejected value. All issues of a run are returned together."""

    code: str
    sheet: str
    row: int | None = None
    entity_id: str | None = None
    field: str | None = None
    message: str


class Farm(Frozen):
    farm_id: str
    farm_name: str
    row: int
    expected_daily_capacity_t: Dec
    expected_mix: dict[Segment, Dec]
    actual_t: dict[Segment, int]

    def expected_segment_t(self, segment: Segment) -> Decimal:
        """Expected tonnes for one segment = expected capacity x expected mix."""
        return self.expected_daily_capacity_t * self.expected_mix[segment]

    @property
    def actual_total_t(self) -> int:
        return sum(self.actual_t.values())


class Client(Frozen):
    client_id: str
    client_name: str
    row: int
    acceptance_mode: AcceptanceMode
    requested_segment: Segment
    demand_t: int
    export_price_per_t_eur: Dec


class Station(Frozen):
    station_id: str
    export_conditioning_capacity_t: int
    local_market_ratio: Dec


class ReferencePrice(Frozen):
    segment: Segment
    reference_export_price_per_t_eur: Dec


class SourceData(Frozen):
    """Everything the planning engine is allowed to read. Validated, never repaired."""

    farms: list[Farm]
    clients: list[Client]
    station: Station
    reference_prices: list[ReferencePrice]

    def reference_price(self, segment: Segment) -> Decimal:
        for price in self.reference_prices:
            if price.segment is segment:
                return price.reference_export_price_per_t_eur
        raise KeyError(f"no reference price for segment {segment.value}")

    def fingerprint(self) -> str:
        """Stable sha256 of the normalised source data, used as plan_id."""
        parts: list[str] = []
        for farm in self.farms:
            mix = ",".join(f"{segment.value}={farm.expected_mix[segment]}" for segment in Segment)
            actual = ",".join(f"{segment.value}={farm.actual_t[segment]}" for segment in Segment)
            parts.append(
                f"farm|{farm.farm_id}|{farm.farm_name}|"
                f"{farm.expected_daily_capacity_t}|{mix}|{actual}"
            )
        for client in self.clients:
            parts.append(
                f"client|{client.client_id}|{client.client_name}|"
                f"{client.acceptance_mode.value}|{client.requested_segment.value}|"
                f"{client.demand_t}|{client.export_price_per_t_eur}"
            )
        parts.append(
            f"station|{self.station.station_id}|"
            f"{self.station.export_conditioning_capacity_t}|{self.station.local_market_ratio}"
        )
        for price in self.reference_prices:
            parts.append(
                f"price|{price.segment.value}|{price.reference_export_price_per_t_eur}"
            )
        payload = "\n".join(parts).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def as_json_value(value: Any) -> Any:
    """Small helper for places that need a plain JSON number from a Decimal."""
    return float(value) if isinstance(value, Decimal) else value


# --------------------------------------------------------------- planning results


class ClientStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNSERVED = "UNSERVED"


class ShortageReason(str, Enum):
    STATION_CAPACITY_REACHED = "STATION_CAPACITY_REACHED"
    INSUFFICIENT_COMPATIBLE_SEGMENT = "INSUFFICIENT_COMPATIBLE_SEGMENT"


class AllocationRow(BaseModel):
    """One farm segment volume sent to one client. Consecutive 5 t steps are merged."""

    row_id: int
    processing_order: int
    farm_id: str
    segment: Segment
    client_id: str
    tonnes: int
    quality_upgrade: int
    price_per_t: Dec
    revenue_eur: Dec


class ClientResult(BaseModel):
    client_id: str
    client_name: str
    processing_order: int
    mode: AcceptanceMode
    requested_segment: Segment
    accepted_segments: list[Segment]
    price_per_t: Dec
    demand_t: int
    allocated_t: int
    remaining_t: int
    revenue_eur: Dec
    status: ClientStatus
    reason: ShortageReason | None = None


class ResidualRow(BaseModel):
    """Fruit that was not exported and goes to the local market."""

    farm_id: str
    segment: Segment
    tonnes: int
    reference_price_per_t: Dec
    local_value_eur: Dec


class SegmentComparison(BaseModel):
    segment: Segment
    expected_t: Dec
    actual_t: int
    variance_t: Dec
    exported_t: int
    local_t: int


class FarmSegmentComparison(BaseModel):
    expected_t: Dec
    actual_t: int
    variance_t: Dec
    exported_t: int
    local_t: int


class FarmComparison(BaseModel):
    farm_id: str
    farm_name: str
    expected_total_t: Dec
    actual_total_t: int
    variance_total_t: Dec
    exported_total_t: int
    local_total_t: int
    segments: dict[Segment, FarmSegmentComparison]


class FarmSegmentVariance(BaseModel):
    farm_id: str
    segment: Segment
    variance_t: Dec


class RiskLink(BaseModel):
    """Why one client is short, linked to the farm and segment gaps or to capacity."""

    client_id: str
    reason: ShortageReason
    shortfall_t: int
    segments_involved: list[Segment]
    farms_below_plan: list[FarmSegmentVariance]
    served_before: list[str]


class Kpis(BaseModel):
    expected_plan_total_t: Dec
    actual_received_t: int
    station_capacity_t: int
    export_volume_t: int
    local_volume_t: int
    export_rate: Dec | None
    station_utilization: Dec | None
    export_revenue_eur: Dec
    local_value_eur: Dec
    total_value_eur: Dec
    at_risk_clients: int
    # Indicative only: what the local tonnes would have been worth at the export
    # reference price of their segment, minus what the local market pays.
    local_value_at_reference_eur: Dec
    value_lost_to_local_eur: Dec


class Invariant(BaseModel):
    name: str
    passed: bool
    detail: str


class PlanResult(BaseModel):
    kpis: Kpis
    segment_comparison: list[SegmentComparison]
    farm_comparison: list[FarmComparison]
    clients: list[ClientResult]
    allocations: list[AllocationRow]
    residuals: list[ResidualRow]
    risk_links: list[RiskLink]
    invariants: list[Invariant]
