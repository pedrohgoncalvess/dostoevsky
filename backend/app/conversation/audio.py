import io
import math
import wave

from utils import get_env_var


# AUDIO_MIN_DURATION_MS  — discard clips shorter than this (default: 250 ms)
# AUDIO_MIN_RMS          — discard clips with RMS energy below this (default: 200)
# AUDIO_MIN_PEAK         — discard clips whose peak amplitude is below this (default: 800)
_MIN_DURATION_MS = float(get_env_var("AUDIO_MIN_DURATION_MS") or "250")
_MIN_RMS = float(get_env_var("AUDIO_MIN_RMS") or "200")
_MIN_PEAK = float(get_env_var("AUDIO_MIN_PEAK") or "800")

# Default sample rate assumed for raw PCM (no container).
_DEFAULT_SAMPLE_RATE = 24_000


def analyze_noise(audio: bytes, audio_format: str) -> dict:
    """
    Lightweight energy-based VAD.

    Returns a dict with:
      - supported  (bool)  — False when the format can't be analysed
      - is_noise   (bool)  — True when the clip is considered silence/noise
      - rms        (float) — root-mean-square amplitude of the signal
      - peak       (float) — absolute peak amplitude
      - duration_ms(float) — clip duration in milliseconds
      - reason     (str)   — human-readable explanation
    """
    pcm, sample_rate = _extract_pcm16(audio, audio_format)

    if pcm is None:
        return {
            "supported": False,
            "is_noise": False,
            "rms": 0.0,
            "duration_ms": 0.0,
            "reason": "noise_analysis_requires_pcm_or_wav",
        }

    samples = [
        int.from_bytes(pcm[i: i + 2], byteorder="little", signed=True)
        for i in range(0, len(pcm) - 1, 2)
    ]
    if not samples:
        return {
            "supported": True,
            "is_noise": True,
            "rms": 0.0,
            "duration_ms": 0.0,
            "reason": "empty_audio",
        }

    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    peak = float(max(abs(s) for s in samples))
    # Use the sample rate from the WAV header (or the PCM default) so that
    # duration is accurate regardless of what rate the client records at.
    duration_ms = len(samples) / sample_rate * 1000

    is_noise = duration_ms < _MIN_DURATION_MS or rms < _MIN_RMS or peak < _MIN_PEAK
    reason = "low_energy_or_too_short" if is_noise else "speech_candidate"

    return {
        "supported": True,
        "is_noise": is_noise,
        "rms": round(rms, 2),
        "peak": peak,
        "duration_ms": round(duration_ms, 2),
        "reason": reason,
    }


def _extract_pcm16(audio: bytes, audio_format: str) -> tuple[bytes | None, int]:
    """
    Return (raw_pcm16_bytes, sample_rate).

    For PCM/raw input the sample rate is assumed to be ``_DEFAULT_SAMPLE_RATE``.
    For WAV input the sample rate is read from the file header.
    Returns ``(None, 0)`` for unsupported formats.
    """
    normalized = audio_format.lower().strip(".")

    if normalized in {"pcm", "raw"}:
        return audio, _DEFAULT_SAMPLE_RATE

    if normalized != "wav":
        return None, 0

    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if wav.getsampwidth() != 2:
                # Only 16-bit PCM is supported.
                return None, 0
            return wav.readframes(wav.getnframes()), wav.getframerate()
    except wave.Error:
        return None, 0
