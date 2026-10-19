"""Optional on-device AI through Ollama (https://ollama.com).

Everything here is opt-in and local: requests go to an Ollama server on this machine (default
http://127.0.0.1:11434) and nothing is sent anywhere else. The model's output is only ever shown to
the user as text; it is never executed and never changes data by itself, so instructions hidden in a
note cannot make it do anything beyond writing a misleading summary.
"""

import os
from urllib.parse import urlparse

import httpx

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
STATUS_TIMEOUT_SECONDS = 2.0
GENERATE_TIMEOUT_SECONDS = 180.0


class AIError(Exception):
    """Base class for AI feature errors."""


class AIDisabledError(AIError):
    """AI features are switched off in settings."""


class AIUnavailableError(AIError):
    """Ollama can't be reached, or has no suitable model installed."""


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("TASKFLOW_OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/")
        self._transport = transport

    @property
    def is_local(self) -> bool:
        return (urlparse(self.base_url).hostname or "") in LOOPBACK_HOSTS

    def _request(self, method: str, path: str, *, json: dict | None = None, timeout: float) -> dict:
        try:
            with httpx.Client(timeout=timeout, transport=self._transport) as client:
                response = client.request(method, f"{self.base_url}{path}", json=json)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise AIUnavailableError("The local model took too long to respond.") from exc
        except httpx.HTTPStatusError as exc:
            detail = ""
            try:
                detail = str(exc.response.json().get("error", ""))
            except ValueError:
                pass
            raise AIUnavailableError(detail or f"Ollama returned HTTP {exc.response.status_code}.") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AIUnavailableError(
                f"Could not reach Ollama at {self.base_url}. Is it installed and running?"
            ) from exc

    def list_models(self) -> list[str]:
        data = self._request("GET", "/api/tags", timeout=STATUS_TIMEOUT_SECONDS)
        return sorted(m["name"] for m in data.get("models", []) if m.get("name"))

    def chat(self, model: str, system: str, user: str) -> str:
        data = self._request(
            "POST",
            "/api/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=GENERATE_TIMEOUT_SECONDS,
        )
        content = (data.get("message") or {}).get("content", "").strip()
        if not content:
            raise AIUnavailableError("The model returned an empty response.")
        return content

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        data = self._request(
            "POST",
            "/api/embed",
            json={"model": model, "input": texts},
            timeout=GENERATE_TIMEOUT_SECONDS,
        )
        vectors = data.get("embeddings") or []
        if len(vectors) != len(texts):
            raise AIUnavailableError("The embedding model returned an unexpected response.")
        return vectors


def is_embedding_model(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in ("embed", "minilm", "bge-", "e5-", "gte-"))


def pick_chat_model(installed: list[str], preferred: str) -> str | None:
    """The user's chosen model if it is installed, else the first installed non-embedding model."""
    if preferred and preferred in installed:
        return preferred
    return next((m for m in installed if not is_embedding_model(m)), None)


def pick_embed_model(installed: list[str], preferred: str) -> str | None:
    if preferred and preferred in installed:
        return preferred
    return next((m for m in installed if is_embedding_model(m)), None)
