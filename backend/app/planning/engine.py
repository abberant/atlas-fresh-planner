"""The deterministic planning policy.

`plan` is a pure function: no file access, no globals, no clock, no randomness.
The same validated input always gives the same output, byte for byte.

Policy, in order:
1. Supply comes from the actual A/B/C/D tonnes of each farm, one balance per
   (farm, segment). Expected values are only used for comparison.
2. Clients are processed by export price descending, ties broken by client_id.
3. For one client, only compatible supply with a positive balance is considered,
   sorted by smallest quality upgrade first, then by farm_id.
4. Tonnes are taken in 5 t steps until the demand is met, the compatible supply
   is empty, or the shared station capacity is reached.
5. Whatever is left after every client goes to the local market.

No language model is involved anywhere in this file.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.models import (
    AllocationRow,
    Client,
    ClientResult,
    ClientStatus,
    PlanResult,
    ResidualRow,
    ShortageReason,
    SourceData,
)
from app.domain.segments import Segment, accepted_segments, quality_upgrade
from app.planning.comparison import (
    build_farm_comparison,
    build_segment_comparison,
    exported_by_farm_segment,
)
from app.planning.invariants import InvariantViolation, check_invariants
from app.planning.kpis import compute_kpis
from app.planning.risk_links import build_risk_links

STEP_T = 5

SupplyKey = tuple[str, Segment]


def client_processing_order(clients: list[Client]) -> list[Client]:
    """Highest price first. Equal prices are broken by client_id, so the order is stable."""
    return sorted(clients, key=lambda client: (-client.export_price_per_t_eur, client.client_id))


def _supply_balances(source: SourceData) -> dict[SupplyKey, int]:
    return {
        (farm.farm_id, segment): farm.actual_t[segment]
        for farm in source.farms
        for segment in Segment
    }


def plan(source: SourceData) -> PlanResult:
    """Build today's farm to client plan from validated source data."""
    balances = _supply_balances(source)
    capacity_left = source.station.export_conditioning_capacity_t

    allocations: list[AllocationRow] = []
    client_results: list[ClientResult] = []
    next_row_id = 1

    for processing_order, client in enumerate(client_processing_order(source.clients), start=1):
        accepted = accepted_segments(client.acceptance_mode, client.requested_segment)
        demand_left = client.demand_t

        # Best fit first: smallest quality upgrade, then farm_id. The key never
        # changes while we allocate, so one pass over the sorted list is enough.
        candidates = sorted(
            (key for key in balances if key[1] in accepted and balances[key] > 0),
            key=lambda key: (quality_upgrade(client.requested_segment, key[1]), key[0]),
        )

        for farm_id, segment in candidates:
            if demand_left <= 0 or capacity_left < STEP_T:
                break
            take = min(balances[(farm_id, segment)], demand_left, capacity_left)
            take -= take % STEP_T  # allocate in whole 5 t steps only
            if take <= 0:
                continue

            price = client.export_price_per_t_eur
            allocations.append(
                AllocationRow(
                    row_id=next_row_id,
                    processing_order=processing_order,
                    farm_id=farm_id,
                    segment=segment,
                    client_id=client.client_id,
                    tonnes=take,
                    quality_upgrade=quality_upgrade(client.requested_segment, segment),
                    price_per_t=price,
                    revenue_eur=Decimal(take) * price,
                )
            )
            next_row_id += 1
            balances[(farm_id, segment)] -= take
            demand_left -= take
            capacity_left -= take

        allocated = client.demand_t - demand_left
        if allocated == client.demand_t:
            status = ClientStatus.COMPLETE  # a client asking for 0 t is complete
        elif allocated == 0:
            status = ClientStatus.UNSERVED
        else:
            status = ClientStatus.PARTIAL

        reason: ShortageReason | None = None
        if status is not ClientStatus.COMPLETE:
            # The station limit takes priority when both happen at the same time.
            reason = (
                ShortageReason.STATION_CAPACITY_REACHED
                if capacity_left < STEP_T
                else ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT
            )

        client_results.append(
            ClientResult(
                client_id=client.client_id,
                client_name=client.client_name,
                processing_order=processing_order,
                mode=client.acceptance_mode,
                requested_segment=client.requested_segment,
                accepted_segments=list(accepted),
                price_per_t=client.export_price_per_t_eur,
                demand_t=client.demand_t,
                allocated_t=allocated,
                remaining_t=demand_left,
                revenue_eur=Decimal(allocated) * client.export_price_per_t_eur,
                status=status,
                reason=reason,
            )
        )

    # Everything not exported goes to the local market, valued at the local ratio
    # times the reference export price of the residual fruit's own segment.
    ratio = source.station.local_market_ratio
    residuals: list[ResidualRow] = []
    for farm in source.farms:
        for segment in Segment:
            tonnes = balances[(farm.farm_id, segment)]
            if tonnes <= 0:
                continue
            reference_price = source.reference_price(segment)
            residuals.append(
                ResidualRow(
                    farm_id=farm.farm_id,
                    segment=segment,
                    tonnes=tonnes,
                    reference_price_per_t=reference_price,
                    local_value_eur=Decimal(tonnes) * ratio * reference_price,
                )
            )

    exported = exported_by_farm_segment(allocations)
    segment_comparison = build_segment_comparison(source, exported)
    farm_comparison = build_farm_comparison(source, exported)
    kpis = compute_kpis(source, allocations, client_results, residuals)
    risk_links = build_risk_links(client_results, allocations, farm_comparison, balances)

    invariants = check_invariants(source, allocations, client_results, residuals)
    failures = [item for item in invariants if not item.passed]
    if failures:
        raise InvariantViolation(failures)

    return PlanResult(
        kpis=kpis,
        segment_comparison=segment_comparison,
        farm_comparison=farm_comparison,
        clients=client_results,
        allocations=allocations,
        residuals=residuals,
        risk_links=risk_links,
        invariants=invariants,
    )
