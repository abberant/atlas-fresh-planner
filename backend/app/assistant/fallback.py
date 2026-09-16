"""Deterministic summaries written by the planning engine, not by a model.

These are shown when no model is configured, or when a model answer was rejected.
They are always labelled in the UI so nobody mistakes them for an AI answer.
"""

from __future__ import annotations

from decimal import Decimal

from app.assistant.grounding import Citation
from app.assistant.questions import QuestionId
from app.domain.models import PlanResult

MAX_FARMS_LISTED = 3


def _t(value: Decimal | int | float) -> str:
    rounded = round(float(value), 1)
    text = str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"
    return f"{text} t"


def _eur(value: Decimal | int | float) -> str:
    return f"EUR {int(round(float(value))):,}"


def _join(parts: list[str]) -> str:
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return f"{', '.join(parts[:-1])} and {parts[-1]}"


def _at_risk_summary(plan: PlanResult) -> tuple[str, list[Citation]]:
    at_risk = [client for client in plan.clients if client.reason is not None]
    citations: list[Citation] = []

    if not at_risk:
        return ("Every client was served in full today. No client is at risk.", citations)

    links = {link.client_id: link for link in plan.risk_links}
    sentences = [
        f"{len(at_risk)} of {len(plan.clients)} clients are short today."
    ]

    for client in at_risk:
        citations.append(Citation(id=client.client_id, type="client"))
        link = links.get(client.client_id)
        if client.reason.value == "STATION_CAPACITY_REACHED":
            why = (
                f"the station was already full at {_t(plan.kpis.station_capacity_t)}"
            )
        else:
            why = f"there was not enough Segment {client.requested_segment.value}"
            if link and link.served_before:
                served = _join(link.served_before)
                verb = "pays more and was" if len(link.served_before) == 1 else "pay more and were"
                why += f", and {served} {verb} served first"
                citations.extend(
                    Citation(id=served, type="client") for served in link.served_before
                )
        sentences.append(
            f"{client.client_id} ({client.mode.value} {client.requested_segment.value}) received "
            f"{_t(client.allocated_t)} of {_t(client.demand_t)}, short {_t(client.remaining_t)}, "
            f"because {why}."
        )

    unique: list[Citation] = []
    for citation in citations:
        if all(existing.id != citation.id for existing in unique):
            unique.append(citation)
    return (" ".join(sentences), unique)


def _segment_gaps_summary(plan: PlanResult) -> tuple[str, list[Citation]]:
    citations: list[Citation] = []
    below = [row for row in plan.segment_comparison if row.variance_t < 0]
    sentences = [
        f"{_t(plan.kpis.actual_received_t)} arrived against a plan of "
        f"{_t(plan.kpis.expected_plan_total_t)}."
    ]

    if not below:
        sentences.append("No quality segment is below plan today.")
    for row in sorted(below, key=lambda item: item.variance_t):
        citations.append(Citation(id=row.segment.value, type="segment"))
        farms = sorted(
            (
                farm
                for farm in plan.farm_comparison
                if farm.segments[row.segment].variance_t < 0
            ),
            key=lambda farm: farm.segments[row.segment].variance_t,
        )[:MAX_FARMS_LISTED]
        farm_text = _join(
            [f"{farm.farm_id} ({_t(farm.segments[row.segment].variance_t)})" for farm in farms]
        )
        citations.extend(Citation(id=farm.farm_id, type="farm") for farm in farms)
        clients = [
            link.client_id
            for link in plan.risk_links
            if row.segment in link.segments_involved
            and link.reason.value == "INSUFFICIENT_COMPATIBLE_SEGMENT"
        ]
        who = f" It leaves {_join(clients)} short." if clients else " No client is short on it."
        citations.extend(Citation(id=client, type="client") for client in clients)
        sentences.append(
            f"Segment {row.segment.value} is {_t(row.variance_t)} against plan"
            f"{f', mostly {farm_text}' if farm_text else ''}.{who}"
        )

    unique: list[Citation] = []
    for citation in citations:
        if all(existing.id != citation.id for existing in unique):
            unique.append(citation)
    return (" ".join(sentences), unique)


def _local_residual_summary(plan: PlanResult) -> tuple[str, list[Citation]]:
    kpis = plan.kpis
    citations: list[Citation] = []

    if not plan.residuals:
        return ("Every tonne received today was exported. Nothing goes to the local market.", [])

    segments = sorted({row.segment.value for row in plan.residuals})
    citations.extend(Citation(id=segment, type="segment") for segment in segments)

    full = kpis.export_volume_t >= kpis.station_capacity_t
    why = (
        f"the station is full at {_t(kpis.station_capacity_t)}"
        if full
        else "no client could take that quality today"
    )

    by_farm = _join(
        [f"{row.farm_id} {_t(row.tonnes)} of Segment {row.segment.value}" for row in plan.residuals]
    )
    citations.extend(Citation(id=row.farm_id, type="farm") for row in plan.residuals)

    sentences = [
        f"{_t(kpis.local_volume_t)} could not be exported because {why}.",
        f"It comes from {by_farm}.",
        f"On the local market it is worth {_eur(kpis.local_value_eur)}, against "
        f"{_eur(kpis.local_value_at_reference_eur)} at the export reference price of the same "
        f"segments.",
    ]

    capacity_hits = [
        link for link in plan.risk_links if link.reason.value == "STATION_CAPACITY_REACHED"
    ]
    for link in capacity_hits:
        citations.append(Citation(id=link.client_id, type="client"))
    if capacity_hits:
        names = _join([f"{link.client_id} ({_t(link.shortfall_t)})" for link in capacity_hits])
        sentences.append(f"The same limit left {names} short.")

    unique: list[Citation] = []
    for citation in citations:
        if all(existing.id != citation.id for existing in unique):
            unique.append(citation)
    return (" ".join(sentences), unique)


SUMMARIES = {
    QuestionId.AT_RISK_CLIENTS: _at_risk_summary,
    QuestionId.SEGMENT_GAPS: _segment_gaps_summary,
    QuestionId.LOCAL_RESIDUAL: _local_residual_summary,
}


def build_summary(question_id: QuestionId, plan: PlanResult) -> tuple[str, list[Citation]]:
    """A summary written from the plan, with the ids it mentions."""
    return SUMMARIES[question_id](plan)
