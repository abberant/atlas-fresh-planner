"""Builders for small synthetic cases.

The engine is a pure function over SourceData, so policy tests do not need a file.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.models import Client, Farm, ReferencePrice, SourceData, Station
from app.domain.segments import AcceptanceMode, Segment

EQUAL_MIX = {segment: Decimal("0.25") for segment in Segment}
DEFAULT_REFERENCE_PRICES = {
    Segment.A: Decimal(1500),
    Segment.B: Decimal(1250),
    Segment.C: Decimal(1000),
    Segment.D: Decimal(750),
}


def make_farm(
    farm_id: str,
    actual: dict[str, int] | None = None,
    capacity: str | int = 0,
    mix: dict[Segment, Decimal] | None = None,
    row: int = 5,
) -> Farm:
    tonnes = {segment: 0 for segment in Segment}
    for key, value in (actual or {}).items():
        tonnes[Segment(key)] = value
    return Farm(
        farm_id=farm_id,
        farm_name=f"Farm {farm_id}",
        row=row,
        expected_daily_capacity_t=Decimal(str(capacity)),
        expected_mix=mix or EQUAL_MIX,
        actual_t=tonnes,
    )


def make_client(
    client_id: str,
    mode: str,
    segment: str,
    demand: int,
    price: str | int,
    row: int = 5,
) -> Client:
    return Client(
        client_id=client_id,
        client_name=f"Client {client_id}",
        row=row,
        acceptance_mode=AcceptanceMode(mode),
        requested_segment=Segment(segment),
        demand_t=demand,
        export_price_per_t_eur=Decimal(str(price)),
    )


def make_source(
    farms: list[Farm],
    clients: list[Client],
    capacity: int = 500,
    ratio: str = "0.1",
    reference_prices: dict[Segment, Decimal] | None = None,
) -> SourceData:
    prices = reference_prices or DEFAULT_REFERENCE_PRICES
    return SourceData(
        farms=farms,
        clients=clients,
        station=Station(
            station_id="STATION-01",
            export_conditioning_capacity_t=capacity,
            local_market_ratio=Decimal(ratio),
        ),
        reference_prices=[
            ReferencePrice(segment=segment, reference_export_price_per_t_eur=prices[segment])
            for segment in Segment
        ],
    )


def rows_as_tuples(allocations) -> list[tuple[str, str, str, int]]:
    """Allocation rows as (farm, segment, client, tonnes) for easy comparison."""
    return [(row.farm_id, row.segment.value, row.client_id, row.tonnes) for row in allocations]
