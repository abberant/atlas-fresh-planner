"""The grounded assistant endpoint.

The assistant only explains a plan the engine already produced. It never changes
an allocation, never calculates and never confirms anything.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.errors import PlanNotFound
from app.api.plan_store import plan_store
from app.assistant.context import build_context
from app.assistant.fallback import build_summary
from app.assistant.grounding import GroundingError, validate_answer
from app.assistant.providers import (
    SYSTEM_PROMPT,
    ProviderError,
    ProviderNotConfigured,
    ProviderTimeout,
    build_provider,
)
from app.assistant.questions import QUESTION_TEXT, QuestionId, match_free_text, parse_question_id
from app.config import get_settings

logger = logging.getLogger("atlas_fresh")

router = APIRouter(prefix="/api", tags=["assistant"])

UNAVAILABLE_MESSAGE = "This information is not available in today's inputs or plan."


class AskRequest(BaseModel):
    plan_id: str
    question_id: str | None = None
    question_text: str | None = Field(default=None, max_length=500)


class CitationOut(BaseModel):
    id: str
    type: str


class AssistantResponse(BaseModel):
    mode: str  # ai, deterministic_summary, unavailable or error
    provider: str  # anthropic, ollama or none
    answer: str
    citations: list[CitationOut] = []
    error_code: str | None = None
    question_id: str | None = None
    #: The engine summary, offered when an AI answer could not be shown. Never
    #: labelled as an AI answer in the UI.
    fallback_answer: str | None = None
    fallback_citations: list[CitationOut] = []


def _out(citations) -> list[CitationOut]:
    return [CitationOut(id=item.id, type=item.type) for item in citations]


@router.post("/assistant/ask", response_model=AssistantResponse)
def ask(request: AskRequest) -> AssistantResponse:
    stored = plan_store.get(request.plan_id)
    if stored is None:
        raise PlanNotFound(
            "This plan is no longer in memory. Load today's data again and ask once more."
        )

    settings = get_settings()
    provider = build_provider(settings)

    question_id = parse_question_id(request.question_id)
    if question_id is None and request.question_text:
        question_id = match_free_text(request.question_text)

    if question_id is None:
        # An unsupported topic is answered honestly, with no model call at all.
        return AssistantResponse(
            mode="unavailable",
            provider=provider.name,
            answer=UNAVAILABLE_MESSAGE,
            error_code=None,
            question_id=None,
        )

    plan = stored.plan
    context = build_context(question_id, plan)
    summary, summary_citations = build_summary(question_id, plan)
    question = request.question_text or QUESTION_TEXT[question_id]

    try:
        raw = provider.generate(SYSTEM_PROMPT, context, question)
    except ProviderNotConfigured:
        return AssistantResponse(
            mode="deterministic_summary",
            provider=provider.name,
            answer=summary,
            citations=_out(summary_citations),
            error_code="NO_KEY",
            question_id=question_id.value,
        )
    except ProviderTimeout:
        logger.warning("assistant provider timed out")
        return AssistantResponse(
            mode="error",
            provider=provider.name,
            answer="",
            error_code="TIMEOUT",
            question_id=question_id.value,
            fallback_answer=summary,
            fallback_citations=_out(summary_citations),
        )
    except ProviderError as exc:
        logger.warning("assistant provider failed: %s", exc)
        return AssistantResponse(
            mode="error",
            provider=provider.name,
            answer="",
            error_code="PROVIDER_ERROR",
            question_id=question_id.value,
            fallback_answer=summary,
            fallback_citations=_out(summary_citations),
        )

    try:
        grounded = validate_answer(raw, plan, context)
    except GroundingError as exc:
        logger.warning("assistant answer rejected: %s", exc.reason)
        return AssistantResponse(
            mode="error",
            provider=provider.name,
            answer="",
            error_code="INVALID_OUTPUT",
            question_id=question_id.value,
            fallback_answer=summary,
            fallback_citations=_out(summary_citations),
        )

    if grounded.unavailable:
        return AssistantResponse(
            mode="unavailable",
            provider=provider.name,
            answer=UNAVAILABLE_MESSAGE,
            question_id=question_id.value,
        )

    return AssistantResponse(
        mode="ai",
        provider=provider.name,
        answer=grounded.answer,
        citations=_out(grounded.citations),
        error_code=None,
        question_id=question_id.value,
    )
