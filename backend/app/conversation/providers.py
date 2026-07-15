from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import numpy as np

from app.conversation.audio_utils import float_to_pcm16, pcm_to_wav
from app.conversation.openrouter import OpenRouterClient
from utils import get_env_var

if TYPE_CHECKING:
    from database.models.ai import Model

logger = logging.getLogger(__name__)

KOKORO_MODEL_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    "kokoro-v1.0.onnx"
)
KOKORO_VOICES_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    "voices-v1.0.bin"
)


class STTProvider(ABC):
    @abstractmethod
    async def transcribe(
        self,
        audio: bytes,
        audio_format: str,
        language: str | None = None,
    ) -> str:
        """Transcribe audio bytes to text."""


class TTSProvider(ABC):
    @abstractmethod
    async def speech(
        self,
        text: str,
        voice: str | None = None,
        response_format: str = "pcm",
    ) -> bytes:
        """Synthesize text into audio bytes."""


class OpenRouterSTTProvider(STTProvider):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.client = OpenRouterClient()

    async def transcribe(
        self,
        audio: bytes,
        audio_format: str,
        language: str | None = None,
    ) -> str:
        return await self.client.transcribe(audio, audio_format, self.model_id, language)


class OpenRouterTTSProvider(TTSProvider):
    def __init__(self, model_id: str, voice: str, response_format: str = "pcm") -> None:
        self.model_id = model_id
        self.voice = voice
        self.response_format = response_format
        self.client = OpenRouterClient()

    async def speech(self, text: str, voice: str | None = None, response_format: str = "pcm") -> bytes:
        return await self.client.speech(
            text,
            self.model_id,
            voice or self.voice,
            response_format or self.response_format,
        )


class FasterWhisperSTTProvider(STTProvider):
    """Local STT using faster-whisper (CTranslate2-based Whisper)."""

    _model = None
    # Lock serialises the first load so only one thread initialises the model
    # even when multiple async tasks arrive before the model is ready.
    _lock = asyncio.Lock()

    def __init__(
        self,
        model_size: str | None = None,
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        self.model_size = model_size or get_env_var("LOCAL_STT_MODEL_SIZE") or "base"
        self.device = device or get_env_var("LOCAL_STT_DEVICE") or "auto"
        self.compute_type = compute_type or get_env_var("LOCAL_STT_COMPUTE_TYPE") or "default"

    async def _ensure_model(self):
        """Load the model exactly once, safely, across concurrent callers."""
        if FasterWhisperSTTProvider._model is not None:
            return FasterWhisperSTTProvider._model

        async with FasterWhisperSTTProvider._lock:
            # Double-check after acquiring the lock.
            if FasterWhisperSTTProvider._model is None:
                logger.info("Loading faster-whisper model: %s", self.model_size)
                model_size = self.model_size
                device = self.device
                compute_type = self.compute_type

                def _load():
                    from faster_whisper import WhisperModel
                    cache_dir = get_env_var("LOCAL_MODELS_DIR") or "models"
                    return WhisperModel(
                        model_size,
                        device=device,
                        compute_type=compute_type,
                        download_root=cache_dir
                    )

                FasterWhisperSTTProvider._model = await asyncio.to_thread(_load)

        return FasterWhisperSTTProvider._model

    async def transcribe(
        self,
        audio: bytes,
        audio_format: str,
        language: str | None = None,
    ) -> str:
        if audio_format.lower() in {"pcm", "raw"}:
            audio = pcm_to_wav(audio)
            audio_format = "wav"

        suffix = ".wav" if audio_format.lower() == "wav" else ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name

        try:
            model = await self._ensure_model()
            segments, _info = await asyncio.to_thread(
                lambda: list(model.transcribe(tmp_path, language=language)),
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        finally:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def ensure_kokoro_model_files(
    model_path: str | None = None,
    voices_path: str | None = None,
) -> tuple[str, str]:
    """Download Kokoro ONNX model and voices bin if not already present.

    This function is intentionally synchronous because it is always called
    inside ``asyncio.to_thread``; do not call it directly from an async context.
    """
    if model_path and voices_path:
        return model_path, voices_path

    cache_dir = Path(get_env_var("LOCAL_MODELS_DIR") or "models")
    cache_dir.mkdir(parents=True, exist_ok=True)
    model_file = cache_dir / "kokoro-v1.0.onnx"
    voices_file = cache_dir / "voices-v1.0.bin"

    _download_if_missing(KOKORO_MODEL_URL, model_file)
    _download_if_missing(KOKORO_VOICES_URL, voices_file)
    return str(model_file), str(voices_file)


def _kokoro_lang_from_voice(voice_code: str) -> str:
    """Kokoro voice prefixes encode the language code (e.g. 'af_heart' -> 'a')."""
    if not voice_code:
        return "en-us"
    prefix = voice_code[0].lower()
    mapping = {
        "a": "en-us",
        "b": "en-gb",
        "e": "es",
        "f": "fr-fr",
        "h": "hi",
        "i": "it",
        "j": "ja",
        "p": "pt-br",
        "z": "zh",
    }
    return mapping.get(prefix, "en-us")


class KokoroTTSProvider(TTSProvider):
    """Local TTS using Kokoro via ONNX Runtime (kokoro-onnx)."""

    _kokoro = None
    # Separate lock for Kokoro to avoid contention with whisper loads.
    _lock = asyncio.Lock()

    def __init__(
        self,
        model_path: str | None = None,
        voices_path: str | None = None,
        voice: str | None = None,
        lang: str | None = None,
    ) -> None:
        self.model_path = model_path or get_env_var("LOCAL_KOKORO_MODEL_PATH")
        self.voices_path = voices_path or get_env_var("LOCAL_KOKORO_VOICES_PATH")
        self.voice = voice or get_env_var("LOCAL_TTS_VOICE") or "af_heart"
        self.lang = lang or get_env_var("LOCAL_TTS_LANG")

    async def _ensure_kokoro(self):
        """Load Kokoro exactly once, safely, across concurrent callers."""
        if KokoroTTSProvider._kokoro is not None:
            return KokoroTTSProvider._kokoro

        async with KokoroTTSProvider._lock:
            if KokoroTTSProvider._kokoro is None:
                model_path = self.model_path
                voices_path = self.voices_path

                def _load():
                    mp, vp = ensure_kokoro_model_files(model_path, voices_path)
                    logger.info("Loading Kokoro ONNX model from %s", mp)
                    from kokoro_onnx import Kokoro
                    return Kokoro(mp, vp)

                KokoroTTSProvider._kokoro = await asyncio.to_thread(_load)

        return KokoroTTSProvider._kokoro

    async def speech(
        self,
        text: str,
        voice: str | None = None,
        response_format: str = "pcm",
    ) -> bytes:
        if not text:
            return b""

        kokoro = await self._ensure_kokoro()
        chosen_voice = voice or self.voice
        lang = self.lang or _kokoro_lang_from_voice(chosen_voice)

        def _synthesize():
            audio, sample_rate = kokoro.create(text, voice=chosen_voice, lang=lang)
            return np.asarray(audio), sample_rate

        audio, sample_rate = await asyncio.to_thread(_synthesize)
        pcm = float_to_pcm16(audio)

        if response_format.lower() == "wav":
            return pcm_to_wav(pcm, sample_rate=sample_rate)
        return pcm


def _download_if_missing(url: str, destination: Path) -> None:
    if destination.exists():
        return
    logger.info("Downloading %s to %s", url, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=300, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(destination, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)


class AudioProviderFactory:
    def __init__(self) -> None:
        self._openrouter_stt: dict[str, OpenRouterSTTProvider] = {}
        self._openrouter_tts: dict[str, OpenRouterTTSProvider] = {}
        self._local_stt: FasterWhisperSTTProvider | None = None
        self._local_tts: KokoroTTSProvider | None = None

    def stt_provider(self, model: Model) -> STTProvider:
        external_id = model.external_id
        if model.type == "local" or external_id.startswith("local:"):
            if self._local_stt is None:
                self._local_stt = FasterWhisperSTTProvider()
            return self._local_stt

        if external_id not in self._openrouter_stt:
            self._openrouter_stt[external_id] = OpenRouterSTTProvider(external_id)
        return self._openrouter_stt[external_id]

    def tts_provider(self, model: Model, voice: str | None = None) -> TTSProvider:
        external_id = model.external_id
        if model.type == "local" or external_id.startswith("local:"):
            if self._local_tts is None:
                self._local_tts = KokoroTTSProvider()
            return self._local_tts

        key = f"{external_id}:{voice}"
        if key not in self._openrouter_tts:
            self._openrouter_tts[key] = OpenRouterTTSProvider(external_id, voice or "tara")
        return self._openrouter_tts[key]
