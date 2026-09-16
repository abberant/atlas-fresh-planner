"""The three questions the assistant is allowed to answer.

Anything else is answered honestly with "not available", never with a guess.
"""

from __future__ import annotations

import re
from enum import Enum


class QuestionId(str, Enum):
    AT_RISK_CLIENTS = "at_risk_clients"
    SEGMENT_GAPS = "segment_gaps"
    LOCAL_RESIDUAL = "local_residual"


#: Words that point a free text question at one of the supported topics.
KEYWORDS: dict[QuestionId, tuple[str, ...]] = {
    QuestionId.AT_RISK_CLIENTS: (
        "risk", "client", "short", "partial", "unserved", "shortfall", "demand", "customer",
    ),
    QuestionId.SEGMENT_GAPS: (
        "segment", "gap", "quality", "variance", "farm", "below plan", "production", "expected",
    ),
    QuestionId.LOCAL_RESIDUAL: (
        "local", "residual", "unexported", "not exported", "leftover", "waste", "downgrade",
    ),
}

QUESTION_TEXT: dict[QuestionId, str] = {
    QuestionId.AT_RISK_CLIENTS: "Which clients are at risk today and why?",
    QuestionId.SEGMENT_GAPS: "Which farm and segment gaps matter most today?",
    QuestionId.LOCAL_RESIDUAL: (
        "Why are tonnes going to the local market and what are they worth?"
    ),
}


def parse_question_id(value: str | None) -> QuestionId | None:
    if value is None:
        return None
    try:
        return QuestionId(value)
    except ValueError:
        return None


def match_free_text(text: str) -> QuestionId | None:
    """Point a typed question at a supported topic, or return None.

    The score is how many keywords of a topic appear in the question. Ties are
    broken by the order of QuestionId, so the same text always gives the same topic.
    """
    lowered = f" {re.sub(r'[^a-z0-9 ]+', ' ', text.lower())} "
    best: QuestionId | None = None
    best_score = 0
    for question_id in QuestionId:
        score = sum(1 for word in KEYWORDS[question_id] if word in lowered)
        if score > best_score:
            best, best_score = question_id, score
    return best
