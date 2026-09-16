"""Headline numbers for the decision summary. Every value is calculated, never stored."""

from __future__ import annotations

from decimal import Decimal

from app.domain.models import (
    AllocationRow,
    ClientResult,
    ClientStatus,
    Kpis,
    ResidualRow,
    SourceData,
)

AT_RISK_STATUSES = (ClientStatus.PARTIAL, ClientStatus.UNSERVED)


def compute_kpis(
    source: SourceData,
    allocations: list[AllocationRow],
    clients: list[ClientResult],
    residuals: list[ResidualRow],
) -> Kpis:
    expected_total = sum(
        (farm.expected_daily_capacity_t for farm in source.farms), Decimal(0)
    )
    actual_received = sum(farm.actual_total_t for farm in source.farms)
    export_volume = sum(row.tonnes for row in allocations)
    local_volume = actual_received - export_volume
    capacity = source.station.export_conditioning_capacity_t

    export_revenue = sum((row.revenue_eur for row in allocations), Decimal(0))
    local_value = sum((row.local_value_eur for row in residuals), Decimal(0))
    local_at_reference = sum(
        (Decimal(row.tonnes) * row.reference_price_per_t for row in residuals), Decimal(0)
    )

    # Guard the divide by zero: an empty day shows "n/a" instead of a wrong 0%.
    export_rate = Decimal(export_volume) / Decimal(actual_received) if actual_received else None
    utilization = Decimal(export_volume) / Decimal(capacity) if capacity else None

    return Kpis(
        expected_plan_total_t=expected_total,
        actual_received_t=actual_received,
        station_capacity_t=capacity,
        export_volume_t=export_volume,
        local_volume_t=local_volume,
        export_rate=export_rate,
        station_utilization=utilization,
        export_revenue_eur=export_revenue,
        local_value_eur=local_value,
        total_value_eur=export_revenue + local_value,
        at_risk_clients=sum(1 for client in clients if client.status in AT_RISK_STATUSES),
        local_value_at_reference_eur=local_at_reference,
        value_lost_to_local_eur=local_at_reference - local_value,
    )
