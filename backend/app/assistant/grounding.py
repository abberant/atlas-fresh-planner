"""Check a model answer against the plan before anyone sees it.

An answer is rejected whole when it mentions an id that is not in the plan or a
number that is not in the context it was given. Nothing is silently corrected.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.models import PlanResult

FARM_PATTERN = re.compile(r"\bF\d{2}\b")
CLIENT_PATTERN = re.compile(r"\bC\d{2}\b")
SEGMENT_PATTERN = re.compile(r"\bsegments?\s+([ABCD])\b", re.IGNORECASE)
NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?")
FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class GroundingError(Exception):
    """The answer did not pass the checks and must not be shown."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class Citation:
    id: str
    type: str  # farm, client or segment


@dataclass
class GroundedAnswer:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    unavailable: bool = False


@dataclass(frozen=True)
class KnownIds:
    farms: frozenset[str]
    clients: frozenset[str]
    segments: frozenset[str]

    def kind(self, identifier: str) -> str | None:
        if identifier in self.farms:
            return "farm"
        if identifier in self.clients:
            return "client"
        if identifier in self.segments:
            return "segment"
        return None


def known_ids(plan: PlanResult) -> KnownIds:
    return KnownIds(
        farms=frozenset(farm.farm_id for farm in plan.farm_comparison),
        clients=frozenset(client.client_id for client in plan.clients),
        segments=frozenset(row.segment.value for row in plan.segment_comparison),
    )


def allowed_numbers(context: Any) -> set[Decimal]:
    """Every number the model may write: the context numbers and their magnitudes.

    A gap of -27.9 t is written by a person as "27.9 t below plan", and the sign is
    carried by the words. Allowing the magnitude of a context number keeps the rule
    that every number must trace back to one the server produced, while not
    rejecting a correct sentence. Nothing else is derived: no sums, no rounding,
    no percentages.
    """
    numbers = context_numbers(context)
    return numbers | {abs(number) for number in numbers}


def context_numbers(context: Any) -> set[Decimal]:
    """Every number the model was allowed to see, as Decimal."""
    found: set[Decimal] = set()
    if isinstance(context, bool):
        return found
    if isinstance(context, (int, float)):
        return {Decimal(str(context))}
    if isinstance(context, dict):
        for value in context.values():
            found |= context_numbers(value)
    elif isinstance(context, (list, tuple)):
        for value in context:
            found |= context_numbers(value)
    return found


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = FENCE_PATTERN.sub("", text)
    return text.strip()


def _normalise_citation(raw: str) -> str:
    text = str(raw).strip()
    match = SEGMENT_PATTERN.fullmatch(text)
    if match:
        return match.group(1)
    return text


def _numbers_in(text: str) -> list[Decimal]:
    # Remove ids first, so C02 and F01 are never read as numbers.
    without_ids = CLIENT_PATTERN.sub(" ", FARM_PATTERN.sub(" ", text))
    numbers: list[Decimal] = []
    for token in NUMBER_PATTERN.findall(without_ids):
        try:
            numbers.append(Decimal(token.replace(",", "")))
        except InvalidOperation:  # pragma: no cover, the pattern only matches digits
            continue
    return numbers


def validate_answer(raw: str, plan: PlanResult, context: dict[str, Any]) -> GroundedAnswer:
    """Parse and check a model answer. Raises GroundingError when it must be rejected."""
    try:
        payload = json.loads(_strip_fences(raw))
    except (json.JSONDecodeError, TypeError) as exc:
        raise GroundingError("the answer was not valid JSON") from exc

    if not isinstance(payload, dict):
        raise GroundingError("the answer was not a JSON object")

    answer = payload.get("answer", "")
    raw_citations = payload.get("citations", [])
    unavailable = bool(payload.get("unavailable", False))

    if not isinstance(answer, str) or not isinstance(raw_citations, list):
        raise GroundingError("the answer did not use the expected fields")

    if unavailable:
        return GroundedAnswer(answer="", citations=[], unavailable=True)

    if not answer.strip():
        raise GroundingError("the answer was empty")

    ids = known_ids(plan)

    citations: list[Citation] = []
    for item in raw_citations:
        identifier = _normalise_citation(item)
        kind = ids.kind(identifier)
        if kind is None:
            raise GroundingError(f"unknown ID in the citations: {item!r}")
        if all(existing.id != identifier for existing in citations):
            citations.append(Citation(id=identifier, type=kind))

    # Ids written inside the answer must exist too, not only the cited ones.
    for identifier in FARM_PATTERN.findall(answer):
        if identifier not in ids.farms:
            raise GroundingError(f"unknown ID in the answer: {identifier}")
    for identifier in CLIENT_PATTERN.findall(answer):
        if identifier not in ids.clients:
            raise GroundingError(f"unknown ID in the answer: {identifier}")
    for segment in SEGMENT_PATTERN.findall(answer):
        if segment not in ids.segments:
            raise GroundingError(f"unknown segment in the answer: Segment {segment}")

    allowed = allowed_numbers(context)
    for number in _numbers_in(answer):
        if number not in allowed:
            raise GroundingError(f"the answer used a number that is not in the plan: {number}")

    if not citations:
        raise GroundingError("the answer cited no ID")

    return GroundedAnswer(answer=answer.strip(), citations=citations, unavailable=False)
