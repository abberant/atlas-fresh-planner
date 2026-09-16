"""Model providers. All share one interface, so the rest of the app does not care.

Nothing here ever decides an allocation or a number. A provider only turns a
question plus a ready made context into text, which is then checked.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from app.config import Settings

SYSTEM_PROMPT = """You explain an export plan that has already been calculated by a \
deterministic engine. You never calculate anything yourself.

Rules:
- Use only the JSON context given to you. Never use outside knowledge.
- Never write a number that is not present in the context.
- Never mention a farm, client or segment id that is not present in the context.
- Cite the ids you used, for example "C02", "F01" or "Segment A".
- Answer in 3 to 6 short sentences, in plain business English, for a manager.
- Never use field names or codes from the context. Write "short 10 tonnes", not
  "shortfall_t of 10", and "there was not enough Segment A", not
  "INSUFFICIENT_COMPATIBLE_SEGMENT".
- Write segment labels as "Segment A", and tonnes as "10 t" or "10 tonnes".
- If the context cannot answer the question, set unavailable to true.

Reply with JSON only, no code fences, in exactly this shape:
{"answer": "...", "citations": ["C02", "Segment A"], "unavailable": false}"""


class ProviderError(Exception):
    """The provider could not be used."""


class ProviderTimeout(ProviderError):
    """The provider did not answer in time."""


class ProviderNotConfigured(ProviderError):
    """No model is configured, so no model call is made."""


class Provider(Protocol):
    name: str

    def generate(self, system: str, context: dict[str, Any], question: str) -> str: ...


def _why(response: httpx.Response) -> str:
    """The provider's own explanation, for the server log. It never reaches the client."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        return str(body["error"].get("message", ""))[:200]
    return str(body)[:200]


def _user_message(context: dict[str, Any], question: str) -> str:
    return (
        f"Question: {question}\n\n"
        f"Context (JSON, the only facts you may use):\n{json.dumps(context, sort_keys=True)}"
    )


class NoneProvider:
    """The default. No key, no local model, no call."""

    name = "none"

    def generate(self, system: str, context: dict[str, Any], question: str) -> str:
        raise ProviderNotConfigured("no AI provider is configured")


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    def generate(self, system: str, context: dict[str, Any], question: str) -> str:
        if not self._api_key:
            raise ProviderNotConfigured("ANTHROPIC_API_KEY is empty")
        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                timeout=self._timeout,
                headers={
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self._model,
                    "max_tokens": 600,
                    "system": system,
                    "messages": [{"role": "user", "content": _user_message(context, question)}],
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

        if response.status_code >= 400:
            raise ProviderError(f"the provider answered with status {response.status_code}")

        try:
            blocks = response.json()["content"]
            return "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        except (KeyError, ValueError, TypeError) as exc:
            raise ProviderError("the provider answer could not be read") from exc


class GeminiProvider:
    """Google AI Studio. Has a free tier, so no purchase is needed to try it."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    def generate(self, system: str, context: dict[str, Any], question: str) -> str:
        if not self._api_key:
            raise ProviderNotConfigured("GEMINI_API_KEY is empty")
        try:
            response = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}"
                ":generateContent",
                timeout=self._timeout,
                headers={"x-goog-api-key": self._api_key, "content-type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [
                        {"role": "user", "parts": [{"text": _user_message(context, question)}]}
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        # Room for the whole answer. A truncated answer is rejected
                        # later, so it is cheaper to give the model enough budget.
                        "maxOutputTokens": 2048,
                        "temperature": 0,
                        # This model thinks before answering unless told not to, and
                        # that thinking eats the same budget. We only need it to read
                        # a small context back to us, so it is turned off.
                        "thinkingConfig": {"thinkingBudget": 0},
                    },
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

        if response.status_code >= 400:
            raise ProviderError(
                f"the provider answered with status {response.status_code}: {_why(response)}"
            )

        try:
            candidate = response.json()["candidates"][0]
            parts = candidate["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ProviderError("the provider answer could not be read") from exc

        if candidate.get("finishReason") == "MAX_TOKENS":
            # The answer is cut in half. Say why, instead of letting it fail later
            # as unreadable JSON.
            raise ProviderError("the provider hit its output limit before finishing the answer")
        return text


class OllamaProvider:
    """Free local path. Nothing leaves the machine."""

    name = "ollama"

    def __init__(self, url: str, model: str, timeout_seconds: int) -> None:
        self._url = url.rstrip("/")
        self._model = model
        self._timeout = timeout_seconds

    def generate(self, system: str, context: dict[str, Any], question: str) -> str:
        try:
            response = httpx.post(
                f"{self._url}/api/chat",
                timeout=self._timeout,
                json={
                    "model": self._model,
                    "stream": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": _user_message(context, question)},
                    ],
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout(str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc)) from exc

        if response.status_code >= 400:
            raise ProviderError(f"the provider answered with status {response.status_code}")

        try:
            return response.json()["message"]["content"]
        except (KeyError, ValueError, TypeError) as exc:
            raise ProviderError("the provider answer could not be read") from exc


def build_provider(settings: Settings) -> Provider:
    if settings.ai_provider == "anthropic":
        return AnthropicProvider(
            settings.anthropic_api_key, settings.anthropic_model, settings.ai_timeout_seconds
        )
    if settings.ai_provider == "gemini":
        return GeminiProvider(
            settings.gemini_api_key, settings.gemini_model, settings.ai_timeout_seconds
        )
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings.ollama_url, settings.ollama_model, settings.ai_timeout_seconds)
    return NoneProvider()
