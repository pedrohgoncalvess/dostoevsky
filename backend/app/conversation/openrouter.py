import base64
import json
from typing import Any

import httpx

from utils import get_env_var


class OpenRouterError(RuntimeError):
    pass


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = get_env_var("OPENROUTER_API_KEY")
        self.base_url = get_env_var("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"

        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not configured.")

    async def transcribe(
        self,
        audio: bytes,
        audio_format: str,
        model: str,
        language: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "input_audio": {
                "data": base64.b64encode(audio).decode("ascii"),
                "format": audio_format,
            },
        }
        if language:
            payload["language"] = language

        response = await self._json_request("/audio/transcriptions", payload)
        return response.get("text", "")

    async def chat(self, messages: list[dict[str, str]], model: str, session_id: str) -> str:
        response = await self._json_request(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "session_id": session_id,
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
        response = await self._json_request(
            "/chat/completions",
            {
                "model": model,
                "messages": messages,
                "session_id": session_id,
                "stream": False,
                "response_format": json_schema,
            },
        )
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
        async with httpx.AsyncClient(timeout=90) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{path}",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPStatusError as exc:
                body = exc.response.text
                raise OpenRouterError(
                    f"OpenRouter error {exc.response.status_code}: {body}"
                ) from exc
            except httpx.RequestError as exc:
                raise OpenRouterError(f"OpenRouter connection error: {exc}") from exc
