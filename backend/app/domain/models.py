"""Domain models for the parsed workbook (source) and for validation errors.

Money, ratios and expected tonnes are kept as Decimal so arithmetic stays exact.
They are serialised as plain JSON numbers for the client.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
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
