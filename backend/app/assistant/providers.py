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
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings.ollama_url, settings.ollama_model, settings.ai_timeout_seconds)
    return NoneProvider()
