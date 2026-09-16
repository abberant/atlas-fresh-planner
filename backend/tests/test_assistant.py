"""The assistant boundary: grounded or honest, never invented. No network is used."""

from __future__ import annotations

import json
from typing import Any, Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.plan_store import plan_store
from app.assistant.context import build_context
from app.assistant.fallback import build_summary
from app.assistant.grounding import GroundingError, context_numbers, validate_answer
from app.assistant.providers import (
    SYSTEM_PROMPT,
    GeminiProvider,
    ProviderError,
    ProviderNotConfigured,
    ProviderTimeout,
    build_provider,
)
from app.assistant.questions import QuestionId, match_free_text
from app.config import get_settings
from app.main import app
from app.planning.engine import plan as build_plan


class FakeProvider:
    """Answers with whatever the test wants, or raises. It never touches the network."""

    def __init__(self, reply: str | None = None, error: Exception | None = None) -> None:
        self.name = "ollama"
        self._reply = reply
        self._error = error
        self.calls: list[dict[str, Any]] = []

    def generate(self, system: str, context: dict[str, Any], question: str) -> str:
        self.calls.append({"system": system, "context": context, "question": question})
        if self._error:
            raise self._error
        assert self._reply is not None
        return self._reply


@pytest.fixture
def client() -> Iterator[TestClient]:
    plan_store.clear()
    get_settings.cache_clear()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    get_settings.cache_clear()
    plan_store.clear()


@pytest.fixture
def plan_id(client: TestClient) -> str:
    return client.post("/api/plan/seed").json()["plan_id"]


def use_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeProvider) -> None:
    monkeypatch.setattr("app.api.routes_assistant.build_provider", lambda _settings: provider)


def ask(client: TestClient, plan_id: str, **payload: Any) -> dict[str, Any]:
    response = client.post("/api/assistant/ask", json={"plan_id": plan_id, **payload})
    assert response.status_code == 200, response.text
    return response.json()


# ------------------------------------------------------------------ grounded answers


def test_grounded_answer_is_accepted(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    reply = json.dumps(
        {
            "answer": (
                "3 of 10 clients are short today. C02 asked for 50 t and received 40 t, "
                "short 10 t, because Segment A was too small. C09 is short 20 t on Segment B. "
                "C08 is short 30 t because the station is full at 500 t."
            ),
            "citations": ["C02", "C09", "C08", "Segment A"],
            "unavailable": False,
        }
    )
    provider = FakeProvider(reply=reply)
    use_provider(monkeypatch, provider)

    body = ask(client, plan_id, question_id="at_risk_clients")

    assert body["mode"] == "ai"
    assert body["provider"] == "ollama"
    assert body["error_code"] is None
    assert "C02" in body["answer"]
    assert {c["id"] for c in body["citations"]} == {"C02", "C09", "C08", "A"}
    assert {c["type"] for c in body["citations"]} == {"client", "segment"}


def test_answer_in_a_code_fence_is_still_read(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = json.dumps({"answer": "C02 is short 10 t.", "citations": ["C02"], "unavailable": False})
    use_provider(monkeypatch, FakeProvider(reply=f"```json\n{payload}\n```"))

    body = ask(client, plan_id, question_id="at_risk_clients")
    assert body["mode"] == "ai"


def test_the_context_sent_to_the_provider_is_minimal(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeProvider(reply=json.dumps({"answer": "C02 is short 10 t.", "citations": ["C02"]}))
    use_provider(monkeypatch, provider)
    ask(client, plan_id, question_id="at_risk_clients")

    context = provider.calls[0]["context"]
    assert context["question"] == "at_risk_clients"
    assert len(context["clients_at_risk"]) == 3
    # The whole workbook and all 43 allocation rows are never sent.
    assert "allocations" not in context
    assert "farms" not in context
    assert len(json.dumps(context)) < 4000


# ------------------------------------------------------------------ rejected answers


@pytest.mark.parametrize(
    "label,reply",
    [
        (
            "unknown client",
            json.dumps({"answer": "C99 is short 10 t.", "citations": ["C99"], "unavailable": False}),
        ),
        (
            "unknown farm",
            json.dumps({"answer": "F42 missed its plan.", "citations": ["F42"], "unavailable": False}),
        ),
        (
            "unknown farm in the text only",
            json.dumps({"answer": "F42 let C02 down.", "citations": ["C02"], "unavailable": False}),
        ),
        (
            "invented number",
            json.dumps(
                {"answer": "C02 is short 77 t.", "citations": ["C02"], "unavailable": False}
            ),
        ),
        (
            "no citation",
            json.dumps({"answer": "Some clients are short.", "citations": [], "unavailable": False}),
        ),
        ("not json", "I think C02 is short by a lot."),
        ("empty answer", json.dumps({"answer": "   ", "citations": ["C02"], "unavailable": False})),
    ],
)
def test_bad_answers_are_rejected(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch, label: str, reply: str
) -> None:
    use_provider(monkeypatch, FakeProvider(reply=reply))

    body = ask(client, plan_id, question_id="at_risk_clients")

    assert body["mode"] == "error", label
    assert body["error_code"] == "INVALID_OUTPUT", label
    assert body["answer"] == "", label
    assert body["citations"] == [], label
    # The engine summary is offered instead, and it is never called an AI answer.
    assert body["fallback_answer"]
    assert body["fallback_citations"]


# ------------------------------------------------------------------ provider failures


def test_timeout_is_honest(client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch) -> None:
    use_provider(monkeypatch, FakeProvider(error=ProviderTimeout("too slow")))

    body = ask(client, plan_id, question_id="segment_gaps")

    assert body["mode"] == "error"
    assert body["error_code"] == "TIMEOUT"
    assert body["answer"] == ""
    assert body["fallback_answer"].startswith("560 t arrived")


def test_provider_error_is_honest(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_provider(monkeypatch, FakeProvider(error=ProviderError("boom")))

    body = ask(client, plan_id, question_id="local_residual")

    assert body["mode"] == "error"
    assert body["error_code"] == "PROVIDER_ERROR"
    assert body["answer"] == ""
    assert "boom" not in json.dumps(body)


def test_no_key_falls_back_to_the_engine_summary(client: TestClient, plan_id: str) -> None:
    """The default setup has no provider, so the answer comes from the engine."""
    body = ask(client, plan_id, question_id="at_risk_clients")

    assert body["mode"] == "deterministic_summary"
    assert body["provider"] == "none"
    assert body["error_code"] == "NO_KEY"
    assert "C02" in body["answer"]
    assert body["citations"]


def test_model_says_unavailable(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_provider(
        monkeypatch, FakeProvider(reply=json.dumps({"answer": "", "citations": [], "unavailable": True}))
    )

    body = ask(client, plan_id, question_id="local_residual")

    assert body["mode"] == "unavailable"
    assert body["answer"] == "This information is not available in today's inputs or plan."


# ------------------------------------------------------------------ question routing


def test_unsupported_question_is_not_sent_to_a_provider(
    client: TestClient, plan_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeProvider(reply=json.dumps({"answer": "anything", "citations": ["C02"]}))
    use_provider(monkeypatch, provider)

    body = ask(client, plan_id, question_text="What is the weather in Agadir tomorrow?")

    assert body["mode"] == "unavailable"
    assert body["answer"] == "This information is not available in today's inputs or plan."
    assert provider.calls == [], "an unsupported question must not reach the provider"


def test_unknown_question_id_is_unavailable(client: TestClient, plan_id: str) -> None:
    body = ask(client, plan_id, question_id="tell_me_a_joke")
    assert body["mode"] == "unavailable"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Which clients are at risk?", QuestionId.AT_RISK_CLIENTS),
        ("why is C09 short", QuestionId.AT_RISK_CLIENTS),
        ("which segment gaps matter", QuestionId.SEGMENT_GAPS),
        ("what goes to the local market", QuestionId.LOCAL_RESIDUAL),
        ("what is the capital of Morocco", None),
    ],
)
def test_free_text_routing(text: str, expected: QuestionId | None) -> None:
    assert match_free_text(text) is expected


def test_asking_about_a_forgotten_plan_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/assistant/ask", json={"plan_id": "unknown", "question_id": "at_risk_clients"}
    )
    assert response.status_code == 404
    assert response.json()["error"] == "PLAN_NOT_FOUND"


# ------------------------------------------------------------------ units


def test_validate_answer_checks_numbers_against_the_context(seed_source) -> None:
    plan = build_plan(seed_source)
    context = build_context(QuestionId.LOCAL_RESIDUAL, plan)

    good = json.dumps(
        {"answer": "60 t go local for EUR 4,500.", "citations": ["Segment D"], "unavailable": False}
    )
    assert validate_answer(good, plan, context).answer

    bad = json.dumps(
        {"answer": "61 t go local for EUR 4,500.", "citations": ["Segment D"], "unavailable": False}
    )
    with pytest.raises(GroundingError) as error:
        validate_answer(bad, plan, context)
    assert "61" in str(error.value)


def test_ids_are_never_read_as_numbers(seed_source) -> None:
    """"C02" must not be read as the number 2, which would reject a good answer."""
    plan = build_plan(seed_source)
    context = build_context(QuestionId.AT_RISK_CLIENTS, plan)
    assert 2 not in context_numbers(context) and 1 not in context_numbers(context)

    reply = json.dumps({"answer": "C02 and F01 explain it.", "citations": ["C02"]})
    assert validate_answer(reply, plan, context).answer == "C02 and F01 explain it."


def test_ids_are_checked_against_the_whole_plan(seed_source) -> None:
    """The brief checks ids against the plan, so a real farm may be named in any answer."""
    plan = build_plan(seed_source)
    context = build_context(QuestionId.AT_RISK_CLIENTS, plan)

    with pytest.raises(GroundingError) as error:
        validate_answer(
            json.dumps({"answer": "F42 let C02 down.", "citations": ["C02"]}), plan, context
        )
    assert "F42" in str(error.value)


def test_context_numbers_ignores_booleans() -> None:
    assert context_numbers({"is_full": True, "capacity_t": 500}) == {__import__("decimal").Decimal("500")}


def test_every_question_has_a_summary_and_a_context(seed_source) -> None:
    plan = build_plan(seed_source)
    for question_id in QuestionId:
        text, citations = build_summary(question_id, plan)
        assert text and citations
        assert build_context(question_id, plan)["question"] == question_id.value


def test_default_provider_makes_no_call() -> None:
    get_settings.cache_clear()
    provider = build_provider(get_settings())
    assert provider.name == "none"
    with pytest.raises(ProviderNotConfigured):
        provider.generate("system", {}, "question")


# ------------------------------------------------------- hosted provider wiring


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def test_gemini_provider_reads_the_answer_and_sends_the_key_in_a_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The HTTP shape is pinned here so a provider change cannot pass unnoticed."""
    sent: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        sent["url"] = url
        sent.update(kwargs)
        return FakeResponse(
            200, {"candidates": [{"content": {"parts": [{"text": '{"answer": "ok"}'}]}}]}
        )

    monkeypatch.setattr("app.assistant.providers.httpx.post", fake_post)
    provider = GeminiProvider("test-key", "gemini-2.0-flash", 20)

    assert provider.generate(SYSTEM_PROMPT, {"a": 1}, "why?") == '{"answer": "ok"}'
    assert "gemini-2.0-flash:generateContent" in sent["url"]
    # The key travels in a header, never in the URL, so it cannot leak into a log.
    assert "test-key" not in sent["url"]
    assert sent["headers"]["x-goog-api-key"] == "test-key"
    assert sent["timeout"] == 20
    assert sent["json"]["generationConfig"]["responseMimeType"] == "application/json"
    assert sent["json"]["systemInstruction"]["parts"][0]["text"] == SYSTEM_PROMPT


@pytest.mark.parametrize(
    "label,payload,status",
    [
        ("an error status", {}, 429),
        ("an answer with no candidate", {"candidates": []}, 200),
        ("an answer in an unexpected shape", {"nope": True}, 200),
    ],
)
def test_gemini_provider_failures_become_provider_errors(
    monkeypatch: pytest.MonkeyPatch, label: str, payload: Any, status: int
) -> None:
    monkeypatch.setattr(
        "app.assistant.providers.httpx.post", lambda *a, **k: FakeResponse(status, payload)
    )
    with pytest.raises(ProviderError):
        GeminiProvider("test-key", "gemini-2.0-flash", 20).generate("s", {}, "q")


def test_gemini_provider_timeout_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    def raise_timeout(*args: Any, **kwargs: Any):
        raise httpx.TimeoutException("too slow")

    monkeypatch.setattr("app.assistant.providers.httpx.post", raise_timeout)
    with pytest.raises(ProviderTimeout):
        GeminiProvider("test-key", "gemini-2.0-flash", 20).generate("s", {}, "q")


def test_gemini_without_a_key_makes_no_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args: Any, **kwargs: Any):
        raise AssertionError("no HTTP call may be made without a key")

    monkeypatch.setattr("app.assistant.providers.httpx.post", fail)
    with pytest.raises(ProviderNotConfigured):
        GeminiProvider("", "gemini-2.0-flash", 20).generate("s", {}, "q")


@pytest.mark.parametrize(
    "provider_name,expected",
    [("none", "none"), ("gemini", "gemini"), ("ollama", "ollama"), ("anthropic", "anthropic")],
)
def test_build_provider_picks_the_configured_path(provider_name: str, expected: str) -> None:
    from app.config import Settings

    settings = Settings(ai_provider=provider_name, gemini_api_key="k", anthropic_api_key="k")
    assert build_provider(settings).name == expected
