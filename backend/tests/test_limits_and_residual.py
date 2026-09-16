"""Hard limits, shortage reasons, the local market and proof that nothing is hard coded."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.models import ShortageReason, SourceData
from app.domain.segments import Segment
from app.planning.engine import plan
from app.planning.invariants import InvariantViolation, check_invariants
from builders import make_client, make_farm, make_source, rows_as_tuples


def _assert_invariants_hold(result) -> None:
    failed = [item.name for item in result.invariants if not item.passed]
    assert not failed, f"invariants failed: {failed}"


def test_invariants_hold_on_the_seed(seed_source: SourceData) -> None:
    _assert_invariants_hold(plan(seed_source))


@pytest.mark.parametrize("capacity", [5, 100, 450, 500, 1000])
def test_invariants_hold_for_any_capacity(seed_source: SourceData, capacity: int) -> None:
    station = seed_source.station.model_copy(update={"export_conditioning_capacity_t": capacity})
    result = plan(seed_source.model_copy(update={"station": station}))

    _assert_invariants_hold(result)
    assert result.kpis.export_volume_t <= capacity


def test_station_capacity_is_shared_across_clients() -> None:
    source = make_source(
        farms=[make_farm("F01", {"B": 100})],
        clients=[
            make_client("C01", "EXACT", "B", 40, 1000),
            make_client("C02", "EXACT", "B", 40, 900),
        ],
        capacity=50,
    )
    result = plan(source)

    assert result.kpis.export_volume_t == 50
    by_id = {client.client_id: client for client in result.clients}
    assert by_id["C01"].allocated_t == 40
    assert by_id["C02"].allocated_t == 10
    assert by_id["C02"].reason is ShortageReason.STATION_CAPACITY_REACHED


def test_capacity_reason_wins_when_supply_and_capacity_run_out_together() -> None:
    """The brief gives the station limit priority when both limits bite at once."""
    source = make_source(
        farms=[make_farm("F01", {"B": 20})],
        clients=[make_client("C01", "EXACT", "B", 50, 1000)],
        capacity=20,
    )
    result = plan(source)

    assert result.clients[0].allocated_t == 20
    assert result.clients[0].reason is ShortageReason.STATION_CAPACITY_REACHED


def test_segment_shortage_reason_when_capacity_is_free() -> None:
    source = make_source(
        farms=[make_farm("F01", {"B": 20})],
        clients=[make_client("C01", "EXACT", "B", 50, 1000)],
        capacity=500,
    )
    result = plan(source)

    assert result.clients[0].reason is ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT


def test_unserved_client_when_no_compatible_supply_exists() -> None:
    source = make_source(
        farms=[make_farm("F01", {"D": 40})],
        clients=[make_client("C01", "EXACT", "A", 20, 1000)],
    )
    result = plan(source)

    assert result.clients[0].status.value == "UNSERVED"
    assert result.clients[0].allocated_t == 0
    assert result.clients[0].reason is ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT


def test_client_with_zero_demand_is_complete() -> None:
    source = make_source(
        farms=[make_farm("F01", {"A": 20})],
        clients=[make_client("C01", "EXACT", "A", 0, 1000)],
    )
    result = plan(source)

    assert result.clients[0].status.value == "COMPLETE"
    assert result.clients[0].reason is None
    assert result.allocations == []
    assert result.kpis.at_risk_clients == 0


def test_no_client_receives_more_than_its_demand() -> None:
    source = make_source(
        farms=[make_farm("F01", {"C": 200})],
        clients=[make_client("C01", "EXACT", "C", 45, 1000)],
    )
    result = plan(source)

    assert result.clients[0].allocated_t == 45
    assert result.kpis.local_volume_t == 155


def test_export_plus_local_equals_received(seed_source: SourceData) -> None:
    result = plan(seed_source)
    assert result.kpis.export_volume_t + result.kpis.local_volume_t == result.kpis.actual_received_t
    assert sum(row.tonnes for row in result.residuals) == result.kpis.local_volume_t


def test_local_value_uses_the_reference_price_of_the_residual_segment() -> None:
    source = make_source(
        farms=[make_farm("F01", {"A": 10, "D": 10})],
        clients=[],
        ratio="0.1",
    )
    result = plan(source)

    by_segment = {row.segment: row for row in result.residuals}
    assert by_segment[Segment.A].local_value_eur == Decimal(10) * Decimal("0.1") * Decimal(1500)
    assert by_segment[Segment.D].local_value_eur == Decimal(10) * Decimal("0.1") * Decimal(750)
    assert result.kpis.local_value_eur == Decimal(1500) + Decimal(750)
    # Indicative figure: what the same tonnes would be worth at the export reference price.
    assert result.kpis.local_value_at_reference_eur == Decimal(22_500)
    assert result.kpis.value_lost_to_local_eur == Decimal(20_250)


def test_changing_a_reference_price_changes_local_value_only(seed_source: SourceData) -> None:
    before = plan(seed_source)
    cheaper_d = [
        price.model_copy(update={"reference_export_price_per_t_eur": Decimal(100)})
        if price.segment is Segment.D
        else price
        for price in seed_source.reference_prices
    ]
    after = plan(seed_source.model_copy(update={"reference_prices": cheaper_d}))

    assert after.kpis.local_value_eur != before.kpis.local_value_eur
    assert after.kpis.local_value_eur == Decimal(60) * Decimal("0.1") * Decimal(100)
    assert after.kpis.export_revenue_eur == before.kpis.export_revenue_eur
    assert [c.client_id for c in after.clients] == [c.client_id for c in before.clients]
    assert rows_as_tuples(after.allocations) == rows_as_tuples(before.allocations)


def test_changing_the_local_ratio_changes_local_value(seed_source: SourceData) -> None:
    station = seed_source.station.model_copy(update={"local_market_ratio": Decimal("0.5")})
    result = plan(seed_source.model_copy(update={"station": station}))

    assert result.kpis.local_value_eur == Decimal(22_500)
    assert result.kpis.export_revenue_eur == plan(seed_source).kpis.export_revenue_eur


def test_lower_capacity_changes_the_outcome(seed_source: SourceData) -> None:
    """Proof that the KPIs are computed, not stored."""
    station = seed_source.station.model_copy(update={"export_conditioning_capacity_t": 450})
    result = plan(seed_source.model_copy(update={"station": station}))

    assert result.kpis.export_volume_t == 450
    assert result.kpis.local_volume_t == 110
    assert result.kpis.export_revenue_eur < plan(seed_source).kpis.export_revenue_eur
    assert result.kpis.at_risk_clients > plan(seed_source).kpis.at_risk_clients
    assert any(
        client.reason is ShortageReason.STATION_CAPACITY_REACHED for client in result.clients
    )


def test_changing_a_farm_actual_changes_the_plan(seed_source: SourceData) -> None:
    farms = list(seed_source.farms)
    first = farms[0]
    farms[0] = first.model_copy(
        update={"actual_t": {**first.actual_t, Segment.A: first.actual_t[Segment.A] + 10}}
    )
    result = plan(seed_source.model_copy(update={"farms": farms}))
    before = plan(seed_source)

    assert result.kpis.actual_received_t == before.kpis.actual_received_t + 10
    by_id = {client.client_id: client for client in result.clients}
    assert by_id["C02"].allocated_t == 50  # the extra Segment A closes the C02 gap
    assert by_id["C02"].status.value == "COMPLETE"


def test_empty_day_shows_no_export_rate() -> None:
    source = make_source(farms=[make_farm("F01")], clients=[make_client("C01", "EXACT", "A", 10, 900)])
    result = plan(source)

    assert result.kpis.actual_received_t == 0
    assert result.kpis.export_rate is None
    assert result.kpis.station_utilization == Decimal(0)


def test_invariant_violation_is_raised_not_returned(seed_source: SourceData) -> None:
    """A broken plan must never reach the user as a valid plan."""
    result = plan(seed_source)
    tampered = [row.model_copy(update={"tonnes": row.tonnes + 5}) for row in result.allocations]
    checks = check_invariants(seed_source, tampered, result.clients, result.residuals)

    failed = [item.name for item in checks if not item.passed]
    assert "export_within_station_capacity" in failed
    with pytest.raises(InvariantViolation):
        raise InvariantViolation([item for item in checks if not item.passed])
