"""Quality rules: EXACT takes one segment, MINIMUM takes that one or better."""

from __future__ import annotations

import pytest

from app.domain.segments import AcceptanceMode, Segment, accepted_segments, accepts, quality_upgrade
from app.planning.engine import plan
from builders import make_client, make_farm, make_source, rows_as_tuples


def test_accepted_segments_rules() -> None:
    assert accepted_segments(AcceptanceMode.EXACT, Segment.B) == (Segment.B,)
    assert accepted_segments(AcceptanceMode.MINIMUM, Segment.B) == (Segment.A, Segment.B)
    assert accepted_segments(AcceptanceMode.MINIMUM, Segment.D) == tuple(Segment)


@pytest.mark.parametrize(
    "mode,requested,supplied,expected",
    [
        ("EXACT", "B", "B", True),
        ("EXACT", "B", "A", False),
        ("EXACT", "B", "C", False),
        ("MINIMUM", "C", "C", True),
        ("MINIMUM", "C", "A", True),
        ("MINIMUM", "C", "D", False),
    ],
)
def test_accepts(mode: str, requested: str, supplied: str, expected: bool) -> None:
    assert accepts(AcceptanceMode(mode), Segment(requested), Segment(supplied)) is expected


def test_quality_upgrade_levels() -> None:
    assert quality_upgrade(Segment.C, Segment.C) == 0
    assert quality_upgrade(Segment.C, Segment.B) == 1
    assert quality_upgrade(Segment.C, Segment.A) == 2


def test_exact_client_never_receives_another_segment() -> None:
    source = make_source(
        farms=[make_farm("F01", {"A": 50, "C": 50})],
        clients=[make_client("C01", "EXACT", "B", 50, 1000)],
    )
    result = plan(source)

    assert result.allocations == []
    assert result.clients[0].status.value == "UNSERVED"
    assert result.clients[0].reason.value == "INSUFFICIENT_COMPATIBLE_SEGMENT"
    assert result.kpis.local_volume_t == 100


def test_minimum_client_uses_the_smallest_upgrade_first() -> None:
    """MINIMUM C with no C supply takes B before A, because B is the smaller upgrade."""
    source = make_source(
        farms=[make_farm("F01", {"A": 20, "B": 20})],
        clients=[make_client("C01", "MINIMUM", "C", 30, 1000)],
    )
    result = plan(source)

    assert rows_as_tuples(result.allocations) == [("F01", "B", "C01", 20), ("F01", "A", "C01", 10)]
    upgrades = {(row.segment.value, row.quality_upgrade) for row in result.allocations}
    assert upgrades == {("B", 1), ("A", 2)}


def test_exact_segment_is_used_before_any_upgrade() -> None:
    source = make_source(
        farms=[make_farm("F01", {"A": 20, "B": 20, "C": 20})],
        clients=[make_client("C01", "MINIMUM", "C", 30, 1000)],
    )
    result = plan(source)

    assert rows_as_tuples(result.allocations) == [("F01", "C", "C01", 20), ("F01", "B", "C01", 10)]


def test_equal_upgrade_is_broken_by_farm_id() -> None:
    source = make_source(
        farms=[
            make_farm("F03", {"B": 10}),
            make_farm("F01", {"B": 10}),
            make_farm("F02", {"B": 10}),
        ],
        clients=[make_client("C01", "EXACT", "B", 25, 1000)],
    )
    result = plan(source)

    assert rows_as_tuples(result.allocations) == [
        ("F01", "B", "C01", 10),
        ("F02", "B", "C01", 10),
        ("F03", "B", "C01", 5),
    ]


def test_upgrade_is_reported_on_every_row() -> None:
    source = make_source(
        farms=[make_farm("F01", {"A": 10})],
        clients=[make_client("C01", "MINIMUM", "D", 10, 1000)],
    )
    result = plan(source)

    assert result.allocations[0].quality_upgrade == 3
