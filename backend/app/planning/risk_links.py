"""Link every client at risk to the farm and segment gaps, or to the station limit.

This is the connection between the Production view and the Commercial view.
Nothing here is written by hand: the links are derived from the plan.
"""

from __future__ import annotations

from app.domain.models import (
    AllocationRow,
    ClientResult,
    ClientStatus,
    FarmComparison,
    FarmSegmentVariance,
    RiskLink,
    ShortageReason,
)
from app.domain.segments import Segment, rank

SupplyKey = tuple[str, Segment]
AT_RISK_STATUSES = (ClientStatus.PARTIAL, ClientStatus.UNSERVED)


def build_risk_links(
    clients: list[ClientResult],
    allocations: list[AllocationRow],
    farm_comparison: list[FarmComparison],
    residual_balances: dict[SupplyKey, int],
) -> list[RiskLink]:
    links: list[RiskLink] = []

    for client in clients:
        if client.status not in AT_RISK_STATUSES or client.reason is None:
            continue

        accepted = list(client.accepted_segments)

        if client.reason is ShortageReason.STATION_CAPACITY_REACHED:
            # The fruit was there, the station was full. Show the segments this
            # client could still have taken.
            involved = [
                segment
                for segment in accepted
                if any(
                    tonnes > 0
                    for (_, balance_segment), tonnes in residual_balances.items()
                    if balance_segment is segment
                )
            ] or accepted
        else:
            involved = accepted

        farms_below: list[FarmSegmentVariance] = []
        for farm in farm_comparison:
            for segment in involved:
                variance = farm.segments[segment].variance_t
                if variance < 0:
                    farms_below.append(
                        FarmSegmentVariance(
                            farm_id=farm.farm_id, segment=segment, variance_t=variance
                        )
                    )
        # Worst gap first, then a stable order so the output never moves around.
        farms_below.sort(key=lambda item: (item.variance_t, item.farm_id, rank(item.segment)))

        served_before: list[str] = []
        for row in allocations:
            if row.processing_order >= client.processing_order:
                continue
            if row.segment in accepted and row.client_id not in served_before:
                served_before.append(row.client_id)

        links.append(
            RiskLink(
                client_id=client.client_id,
                reason=client.reason,
                shortfall_t=client.remaining_t,
                segments_involved=involved,
                farms_below_plan=farms_below,
                served_before=served_before,
            )
        )

    return links
