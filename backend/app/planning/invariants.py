"""Hard limits checked on every run. A failure is a server error, never a plan."""

from __future__ import annotations

from app.domain.models import (
    AllocationRow,
    ClientResult,
    Invariant,
    ResidualRow,
    SourceData,
)
from app.domain.segments import Segment, accepts

STEP_T = 5
SupplyKey = tuple[str, Segment]


class InvariantViolation(RuntimeError):
    """Raised when a computed plan breaks a hard limit. Never shown as a valid plan."""

    def __init__(self, failures: list[Invariant]) -> None:
        self.failures = failures
        detail = "; ".join(f"{item.name}: {item.detail}" for item in failures)
        super().__init__(f"planning invariants failed: {detail}")


def check_invariants(
    source: SourceData,
    allocations: list[AllocationRow],
    clients: list[ClientResult],
    residuals: list[ResidualRow],
) -> list[Invariant]:
    results: list[Invariant] = []
    capacity = source.station.export_conditioning_capacity_t
    export_volume = sum(row.tonnes for row in allocations)
    actual_received = sum(farm.actual_total_t for farm in source.farms)
    local_volume = sum(row.tonnes for row in residuals)

    results.append(
        Invariant(
            name="export_within_station_capacity",
            passed=export_volume <= capacity,
            detail=f"exported {export_volume} t of a {capacity} t station capacity",
        )
    )

    over_demand = [
        client.client_id for client in clients if client.allocated_t > client.demand_t
    ]
    results.append(
        Invariant(
            name="client_allocation_within_demand",
            passed=not over_demand,
            detail=(
                "no client received more than its demand"
                if not over_demand
                else f"clients above demand: {', '.join(over_demand)}"
            ),
        )
    )

    available: dict[SupplyKey, int] = {
        (farm.farm_id, segment): tonnes
        for farm in source.farms
        for segment, tonnes in farm.actual_t.items()
    }
    allocated_supply: dict[SupplyKey, int] = {}
    for row in allocations:
        key = (row.farm_id, row.segment)
        allocated_supply[key] = allocated_supply.get(key, 0) + row.tonnes
    over_supply = [
        f"{farm_id} Segment {segment.value}"
        for (farm_id, segment), tonnes in allocated_supply.items()
        if tonnes > available.get((farm_id, segment), 0)
    ]
    results.append(
        Invariant(
            name="supply_within_farm_segment_actual",
            passed=not over_supply,
            detail=(
                "no farm segment gave more than it received"
                if not over_supply
                else f"farm segments over supply: {', '.join(over_supply)}"
            ),
        )
    )

    clients_by_id = {client.client_id: client for client in clients}
    incompatible = [
        f"{row.farm_id} {row.segment.value} -> {row.client_id}"
        for row in allocations
        if not accepts(
            clients_by_id[row.client_id].mode,
            clients_by_id[row.client_id].requested_segment,
            row.segment,
        )
    ]
    results.append(
        Invariant(
            name="allocations_respect_quality_rule",
            passed=not incompatible,
            detail=(
                "every allocation matches the client quality rule"
                if not incompatible
                else f"incompatible rows: {', '.join(incompatible)}"
            ),
        )
    )

    balanced = export_volume + local_volume == actual_received
    results.append(
        Invariant(
            name="export_plus_local_equals_received",
            passed=balanced,
            detail=f"{export_volume} t exported + {local_volume} t local = {actual_received} t received",
        )
    )

    bad_steps = [row.row_id for row in allocations if row.tonnes % STEP_T != 0]
    bad_demands = [client.client_id for client in clients if client.demand_t % STEP_T != 0]
    results.append(
        Invariant(
            name="quantities_are_5t_steps",
            passed=not bad_steps and not bad_demands,
            detail=(
                "every allocation and demand is a whole multiple of 5 t"
                if not bad_steps and not bad_demands
                else f"allocation rows {bad_steps}, clients {bad_demands}"
            ),
        )
    )

    return results
