import base64
import io
import json
import logging
import wave
from typing import Any

import httpx

from utils import get_env_var

logger = logging.getLogger(__name__)


class OpenRouterError(RuntimeError):
    pass


class OpenRouterClient:
    """
    Thin async wrapper around the OpenRouter HTTP API.

    A single ``httpx.AsyncClient`` is shared for the lifetime of this instance
    so that TCP/TLS connections are reused across calls (keepalive pool).
    Use this class as an async context manager when you need explicit lifecycle
    control, or just instantiate it — the client will be closed when the
    instance is garbage-collected.
    """

    def __init__(self) -> None:
        self.api_key = get_env_var("OPENROUTER_API_KEY")
        self.base_url = get_env_var("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"

        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not configured.")

        # Shared client — reuses TCP connections and TLS sessions.
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=90,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "OpenRouterClient":
        return self

    async def __aexit__(self, *_) -> None:
        await self.aclose()

    async def transcribe(
        self,
        audio: bytes,
        audio_format: str,
        model: str,
        language: str | None = None,
    ) -> str:
        if audio_format.lower() in {"pcm", "raw"}:
            audio = _pcm_to_wav(audio)
            audio_format = "wav"

        prompt = "Please transcribe this audio file."
        if language:
            prompt += f" The audio is in {language}."

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio).decode("ascii"),
                            "format": audio_format,
                        },
                    },
                ],
            }
        ]

        response = await self._json_request(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "stream": False,
            },
        )
        choices = response.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    async def chat(self, messages: list[dict[str, str]], model: str, session_id: str) -> str:
        logger.info("OpenRouter chat payload: %s", messages)
        response = await self._json_request(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "stream": False,
            },
        )
        choices = response.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "")

    async def speech(
        self,
        text: str,
        model: str,
        voice: str,
        response_format: str,
    ) -> bytes:
        return await self._bytes_request(
            "/audio/speech",
            {
                "model": model,
                "input": text,
                "voice": voice,
                "response_format": response_format,
            },
        )

    async def chat_structured(
        self,
        messages: list[dict[str, str]],
        model: str,
        json_schema: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        logger.info("OpenRouter chat_structured payload: %s", messages)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if json_schema:
            payload["response_format"] = json_schema

        response = await self._json_request("/chat/completions", payload)
        choices = response.get("choices") or []
        if not choices:
            return {}
        content = choices[0].get("message", {}).get("content", "")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except json.JSONDecodeError as exc:
            raise OpenRouterError(f"Invalid structured output: {exc}") from exc

    async def embed(self, text: str, model: str) -> list[float]:
        response = await self._json_request(
            "/embeddings",
            {
                "model": model,
                "input": text,
            },
        )
        data = response.get("data") or []
        if not data:
            raise OpenRouterError("No embedding returned.")
        embedding = data[0].get("embedding")
        if not embedding:
            raise OpenRouterError("No embedding values returned.")
        return embedding

    async def _json_request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = await self._bytes_request(path, payload)
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise OpenRouterError(f"Invalid JSON response from OpenRouter: {exc}") from exc

    async def _bytes_request(self, path: str, payload: dict[str, Any]) -> bytes:
        try:
            response = await self._client.post(path, json=payload)
            response.raise_for_status()
            return response.content
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            raise OpenRouterError(
                f"OpenRouter error {exc.response.status_code}: {body}"
            ) from exc
        except httpx.RequestError as exc:
            raise OpenRouterError(f"OpenRouter connection error: {exc}") from exc


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24_000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """Wrap raw PCM16 bytes in a WAV header for APIs that require a container format."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    return buffer.getvalue()
