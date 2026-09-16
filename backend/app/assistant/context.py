"""Build the smallest structured context that can answer one question.

Numbers are rounded here the way they are shown to a person, so an answer can be
checked number by number against this context.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.domain.models import PlanResult
from app.assistant.questions import QuestionId

MAX_FARM_GAPS = 8
MAX_FARMS_PER_LINK = 3


def _t(value: Decimal | int | float) -> float | int:
    """Tonnes, one decimal, whole numbers stay whole."""
    rounded = round(float(value), 1)
    return int(rounded) if rounded == int(rounded) else rounded


def _eur(value: Decimal | int | float) -> int:
    return int(round(float(value)))


def _pct(value: Decimal | None) -> float | None:
    return None if value is None else round(float(value) * 100, 1)


def _client_rule(client: Any) -> str:
    return f"{client.mode.value} {client.requested_segment.value}"


def _at_risk_context(plan: PlanResult) -> dict[str, Any]:
    at_risk = [client for client in plan.clients if client.reason is not None]
    links = {link.client_id: link for link in plan.risk_links}

    return {
        "question": QuestionId.AT_RISK_CLIENTS.value,
        "clients_total": len(plan.clients),
        "clients_at_risk_count": len(at_risk),
        "station": {
            "capacity_t": _t(plan.kpis.station_capacity_t),
            "exported_t": _t(plan.kpis.export_volume_t),
            "utilisation_pct": _pct(plan.kpis.station_utilization),
            "is_full": plan.kpis.export_volume_t >= plan.kpis.station_capacity_t,
        },
        "clients_at_risk": [
            {
                "client_id": client.client_id,
                "rule": _client_rule(client),
                "accepts": [segment.value for segment in client.accepted_segments],
                "price_per_t_eur": _eur(client.price_per_t),
                "demand_t": _t(client.demand_t),
                "allocated_t": _t(client.allocated_t),
                "shortfall_t": _t(client.remaining_t),
                "status": client.status.value,
                "reason": client.reason.value if client.reason else None,
                "segments_involved": [
                    segment.value
                    for segment in (
                        links[client.client_id].segments_involved
                        if client.client_id in links
                        else []
                    )
                ],
                "served_before": (
                    links[client.client_id].served_before if client.client_id in links else []
                ),
                "farms_below_plan": [
                    {
                        "farm_id": item.farm_id,
                        "segment": item.segment.value,
                        "variance_t": _t(item.variance_t),
                    }
                    for item in (
                        links[client.client_id].farms_below_plan[:MAX_FARMS_PER_LINK]
                        if client.client_id in links
                        else []
                    )
                ],
            }
            for client in at_risk
        ],
    }


def _segment_gaps_context(plan: PlanResult) -> dict[str, Any]:
    farm_gaps: list[dict[str, Any]] = []
    for farm in plan.farm_comparison:
        for segment, cell in farm.segments.items():
            if cell.variance_t != 0:
                farm_gaps.append(
                    {
                        "farm_id": farm.farm_id,
                        "segment": segment.value,
                        "variance_t": _t(cell.variance_t),
                    }
                )
    farm_gaps.sort(key=lambda item: (-abs(float(item["variance_t"])), item["farm_id"]))

    clients_by_segment: dict[str, list[str]] = {}
    for link in plan.risk_links:
        if link.reason.value != "INSUFFICIENT_COMPATIBLE_SEGMENT":
            continue
        for segment in link.segments_involved:
            clients_by_segment.setdefault(segment.value, []).append(link.client_id)

    return {
        "question": QuestionId.SEGMENT_GAPS.value,
        "expected_total_t": _t(plan.kpis.expected_plan_total_t),
        "actual_total_t": _t(plan.kpis.actual_received_t),
        "segments": [
            {
                "segment": row.segment.value,
                "expected_t": _t(row.expected_t),
                "actual_t": _t(row.actual_t),
                "variance_t": _t(row.variance_t),
                "exported_t": _t(row.exported_t),
                "local_t": _t(row.local_t),
            }
            for row in plan.segment_comparison
        ],
        "top_farm_gaps": farm_gaps[:MAX_FARM_GAPS],
        "clients_short_by_segment": [
            {"segment": segment, "client_ids": ids} for segment, ids in sorted(clients_by_segment.items())
        ],
    }


def _local_residual_context(plan: PlanResult) -> dict[str, Any]:
    segments_involved = sorted({row.segment.value for row in plan.residuals})
    capacity_hits = [
        link for link in plan.risk_links if link.reason.value == "STATION_CAPACITY_REACHED"
    ]

    return {
        "question": QuestionId.LOCAL_RESIDUAL.value,
        "local_volume_t": _t(plan.kpis.local_volume_t),
        "local_value_eur": _eur(plan.kpis.local_value_eur),
        "value_at_export_reference_eur": _eur(plan.kpis.local_value_at_reference_eur),
        "value_lost_eur": _eur(plan.kpis.value_lost_to_local_eur),
        "actual_received_t": _t(plan.kpis.actual_received_t),
        "station": {
            "capacity_t": _t(plan.kpis.station_capacity_t),
            "exported_t": _t(plan.kpis.export_volume_t),
            "is_full": plan.kpis.export_volume_t >= plan.kpis.station_capacity_t,
        },
        "residuals": [
            {
                "farm_id": row.farm_id,
                "segment": row.segment.value,
                "tonnes": _t(row.tonnes),
                "reference_price_per_t_eur": _eur(row.reference_price_per_t),
                "local_value_eur": _eur(row.local_value_eur),
            }
            for row in plan.residuals
        ],
        "segments_involved": segments_involved,
        "clients_short_on_capacity": [
            {"client_id": link.client_id, "shortfall_t": _t(link.shortfall_t)}
            for link in capacity_hits
        ],
    }


BUILDERS = {
    QuestionId.AT_RISK_CLIENTS: _at_risk_context,
    QuestionId.SEGMENT_GAPS: _segment_gaps_context,
    QuestionId.LOCAL_RESIDUAL: _local_residual_context,
}


def build_context(question_id: QuestionId, plan: PlanResult) -> dict[str, Any]:
    """Only what this question needs. The full workbook is never sent."""
    return BUILDERS[question_id](plan)
