"""Expected versus actual, by segment and by farm, including where the fruit went."""

from __future__ import annotations

from decimal import Decimal

from app.domain.models import (
    AllocationRow,
    FarmComparison,
    FarmSegmentComparison,
    SegmentComparison,
    SourceData,
)
from app.domain.segments import Segment

SupplyKey = tuple[str, Segment]


def exported_by_farm_segment(allocations: list[AllocationRow]) -> dict[SupplyKey, int]:
    exported: dict[SupplyKey, int] = {}
    for row in allocations:
        key = (row.farm_id, row.segment)
        exported[key] = exported.get(key, 0) + row.tonnes
    return exported


def build_segment_comparison(
    source: SourceData,
    exported: dict[SupplyKey, int],
) -> list[SegmentComparison]:
    rows: list[SegmentComparison] = []
    for segment in Segment:
        expected = sum(
            (farm.expected_segment_t(segment) for farm in source.farms), Decimal(0)
        )
        actual = sum(farm.actual_t[segment] for farm in source.farms)
        exported_t = sum(exported.get((farm.farm_id, segment), 0) for farm in source.farms)
        rows.append(
            SegmentComparison(
                segment=segment,
                expected_t=expected,
                actual_t=actual,
                variance_t=Decimal(actual) - expected,
                exported_t=exported_t,
                local_t=actual - exported_t,
            )
        )
    return rows


def build_farm_comparison(
    source: SourceData,
    exported: dict[SupplyKey, int],
) -> list[FarmComparison]:
    rows: list[FarmComparison] = []
    for farm in source.farms:
        segments: dict[Segment, FarmSegmentComparison] = {}
        exported_total = 0
        for segment in Segment:
            expected = farm.expected_segment_t(segment)
            actual = farm.actual_t[segment]
            exported_t = exported.get((farm.farm_id, segment), 0)
            exported_total += exported_t
            segments[segment] = FarmSegmentComparison(
                expected_t=expected,
                actual_t=actual,
                variance_t=Decimal(actual) - expected,
                exported_t=exported_t,
                local_t=actual - exported_t,
            )
        actual_total = farm.actual_total_t
        rows.append(
            FarmComparison(
                farm_id=farm.farm_id,
                farm_name=farm.farm_name,
                expected_total_t=farm.expected_daily_capacity_t,
                actual_total_t=actual_total,
                variance_total_t=Decimal(actual_total) - farm.expected_daily_capacity_t,
                exported_total_t=exported_total,
                local_total_t=actual_total - exported_total,
                segments=segments,
            )
        )
    return rows
