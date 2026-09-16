"""The engine must reproduce the public baseline of the brief, exactly.

The numbers below are the published check values. They live only in this test:
the application code never contains them.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.models import ClientStatus, ShortageReason, SourceData
from app.planning.engine import plan
from builders import rows_as_tuples

# farm, segment, client, tonnes, revenue EUR
EXPECTED_ALLOCATIONS = [
    ("F01", "A", "C01", 25, 37500), ("F02", "A", "C01", 20, 30000), ("F03", "A", "C01", 5, 7500),
    ("F03", "A", "C02", 15, 21750), ("F04", "A", "C02", 15, 21750), ("F05", "A", "C02", 5, 7250),
    ("F07", "A", "C02", 5, 7250),
    ("F01", "B", "C03", 5, 6250), ("F02", "B", "C03", 5, 6250), ("F03", "B", "C03", 10, 12500),
    ("F04", "B", "C03", 10, 12500), ("F05", "B", "C03", 25, 31250), ("F06", "B", "C03", 5, 6250),
    ("F06", "B", "C04", 20, 24000), ("F07", "B", "C04", 15, 18000), ("F08", "B", "C04", 20, 24000),
    ("F09", "B", "C04", 5, 6000), ("F11", "B", "C04", 5, 6000), ("F17", "B", "C04", 5, 6000),
    ("F17", "B", "C09", 20, 23000), ("F18", "B", "C09", 10, 11500),
    ("F06", "C", "C05", 5, 5000), ("F07", "C", "C05", 5, 5000), ("F08", "C", "C05", 10, 10000),
    ("F09", "C", "C05", 25, 25000), ("F10", "C", "C05", 15, 15000),
    ("F10", "C", "C06", 5, 4750), ("F11", "C", "C06", 25, 23750), ("F12", "C", "C06", 25, 23750),
    ("F13", "C", "C06", 5, 4750), ("F14", "C", "C06", 5, 4750), ("F15", "C", "C06", 5, 4750),
    ("F15", "C", "C10", 5, 4500), ("F16", "C", "C10", 5, 4500), ("F17", "C", "C10", 5, 4500),
    ("F18", "C", "C10", 15, 13500), ("F19", "C", "C10", 20, 18000),
    ("F10", "D", "C07", 5, 3750), ("F12", "D", "C07", 5, 3750), ("F13", "D", "C07", 20, 15000),
    ("F14", "D", "C07", 20, 15000),
    ("F14", "D", "C08", 5, 3500), ("F15", "D", "C08", 15, 10500),
]

# order, client, price, demand, allocated, status, reason
EXPECTED_CLIENTS = [
    (1, "C01", 1500, 50, 50, "COMPLETE", None),
    (2, "C02", 1450, 50, 40, "PARTIAL", "INSUFFICIENT_COMPATIBLE_SEGMENT"),
    (3, "C03", 1250, 60, 60, "COMPLETE", None),
    (4, "C04", 1200, 70, 70, "COMPLETE", None),
    (5, "C09", 1150, 50, 30, "PARTIAL", "INSUFFICIENT_COMPATIBLE_SEGMENT"),
    (6, "C05", 1000, 60, 60, "COMPLETE", None),
    (7, "C06", 950, 70, 70, "COMPLETE", None),
    (8, "C10", 900, 50, 50, "COMPLETE", None),
    (9, "C07", 750, 50, 50, "COMPLETE", None),
    (10, "C08", 700, 50, 20, "PARTIAL", "STATION_CAPACITY_REACHED"),
]

# segment: expected, actual, variance
EXPECTED_SEGMENTS = {
    "A": ("101.7", 90, "-11.7"),
    "B": ("168.3", 160, "-8.3"),
    "C": ("207.9", 180, "-27.9"),
    "D": ("122.1", 130, "7.9"),
}

EXPECTED_RESIDUALS = [
    ("F15", "D", 5, 375),
    ("F16", "D", 20, 1500),
    ("F19", "D", 5, 375),
    ("F20", "D", 30, 2250),
]


@pytest.fixture(scope="module")
def baseline(seed_source: SourceData):
    return plan(seed_source)


def test_headline_kpis(baseline) -> None:
    kpis = baseline.kpis
    assert kpis.expected_plan_total_t == Decimal("600.0")
    assert kpis.actual_received_t == 560
    assert kpis.station_capacity_t == 500
    assert kpis.export_volume_t == 500
    assert kpis.local_volume_t == 60
    assert kpis.export_revenue_eur == Decimal(549_500)
    assert kpis.local_value_eur == Decimal(4_500)
    assert kpis.total_value_eur == Decimal(554_000)
    assert kpis.at_risk_clients == 3
    assert kpis.export_rate is not None
    assert round(kpis.export_rate * 100, 1) == Decimal("89.3")
    assert kpis.station_utilization == Decimal(1)


def test_segment_totals_and_variances(baseline) -> None:
    by_segment = {row.segment.value: row for row in baseline.segment_comparison}
    for segment, (expected, actual, variance) in EXPECTED_SEGMENTS.items():
        row = by_segment[segment]
        assert row.expected_t == Decimal(expected), segment
        assert row.actual_t == actual, segment
        assert row.variance_t == Decimal(variance), segment


def test_client_results_in_processing_order(baseline) -> None:
    actual = [
        (
            client.processing_order,
            client.client_id,
            int(client.price_per_t),
            client.demand_t,
            client.allocated_t,
            client.status.value,
            client.reason.value if client.reason else None,
        )
        for client in baseline.clients
    ]
    assert actual == EXPECTED_CLIENTS


def test_allocation_rows_match_the_published_oracle(baseline) -> None:
    assert len(baseline.allocations) == 43
    actual = [
        (row.farm_id, row.segment.value, row.client_id, row.tonnes, int(row.revenue_eur))
        for row in baseline.allocations
    ]
    assert actual == EXPECTED_ALLOCATIONS


def test_baseline_has_no_quality_upgrade(baseline) -> None:
    assert {row.quality_upgrade for row in baseline.allocations} == {0}


def test_local_residual_rows(baseline) -> None:
    actual = [
        (row.farm_id, row.segment.value, row.tonnes, int(row.local_value_eur))
        for row in baseline.residuals
    ]
    assert actual == EXPECTED_RESIDUALS


def test_biggest_farm_variances(baseline) -> None:
    """Spot check of the farm gaps the workspace has to make visible."""
    by_farm = {row.farm_id: row for row in baseline.farm_comparison}
    assert by_farm["F20"].segments["C"].variance_t == Decimal("-18.9")
    assert by_farm["F20"].segments["D"].variance_t == Decimal("21.9")
    assert by_farm["F18"].segments["B"].variance_t == Decimal("-12.4")
    assert by_farm["F01"].segments["A"].variance_t == Decimal("-6.5")
    assert by_farm["F04"].segments["A"].variance_t == Decimal("-6.0")

    below_plan = {row.farm_id for row in baseline.farm_comparison if row.variance_total_t < 0}
    assert below_plan == {
        "F01", "F04", "F06", "F07", "F09", "F10", "F12", "F13", "F15", "F16", "F18", "F19",
    }
    on_plan = {row.farm_id for row in baseline.farm_comparison if row.variance_total_t == 0}
    assert on_plan == {"F02", "F03"}


def test_risk_links_explain_each_client_at_risk(baseline) -> None:
    links = {link.client_id: link for link in baseline.risk_links}
    assert set(links) == {"C02", "C09", "C08"}

    c02 = links["C02"]
    assert c02.reason is ShortageReason.INSUFFICIENT_COMPATIBLE_SEGMENT
    assert c02.shortfall_t == 10
    assert [segment.value for segment in c02.segments_involved] == ["A"]
    assert [(item.farm_id, str(item.variance_t)) for item in c02.farms_below_plan] == [
        ("F01", "-6.5"),
        ("F04", "-6.0"),
        ("F03", "-1.0"),
    ]
    assert c02.served_before == ["C01"]

    c09 = links["C09"]
    assert c09.shortfall_t == 20
    assert [item.farm_id for item in c09.farms_below_plan] == ["F18", "F07", "F06", "F09"]
    assert c09.served_before == ["C03", "C04"]

    c08 = links["C08"]
    assert c08.reason is ShortageReason.STATION_CAPACITY_REACHED
    assert c08.shortfall_t == 30
    assert [segment.value for segment in c08.segments_involved] == ["D"]


def test_all_invariants_pass(baseline) -> None:
    assert baseline.invariants
    assert all(item.passed for item in baseline.invariants), [
        item for item in baseline.invariants if not item.passed
    ]


def test_plan_is_deterministic(seed_source: SourceData) -> None:
    first = plan(seed_source).model_dump_json()
    second = plan(seed_source).model_dump_json()
    assert first == second


def test_status_counts(baseline) -> None:
    statuses = [client.status for client in baseline.clients]
    assert statuses.count(ClientStatus.COMPLETE) == 7
    assert statuses.count(ClientStatus.PARTIAL) == 3
    assert statuses.count(ClientStatus.UNSERVED) == 0
