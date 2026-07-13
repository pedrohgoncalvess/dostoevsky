import io
import math
import wave


def analyze_noise(audio: bytes, audio_format: str) -> dict[str, float | bool | str]:
    pcm = _extract_pcm16(audio, audio_format)
    if not pcm:
        return {
            "supported": False,
            "is_noise": False,
            "rms": 0.0,
            "duration_ms": 0.0,
            "reason": "noise_analysis_requires_pcm_or_wav",
        }

    samples = [
        int.from_bytes(pcm[i:i + 2], byteorder="little", signed=True)
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

    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    peak = max(abs(sample) for sample in samples)
    duration_ms = len(samples) / 24_000 * 1000

    is_noise = duration_ms < 250 or rms < 250 or peak < 900
    reason = "low_energy_or_too_short" if is_noise else "speech_candidate"
    return {
        "supported": True,
        "is_noise": is_noise,
        "rms": round(rms, 2),
        "peak": float(peak),
        "duration_ms": round(duration_ms, 2),
        "reason": reason,
    }


def _extract_pcm16(audio: bytes, audio_format: str) -> bytes | None:
    normalized = audio_format.lower().strip(".")
    if normalized in {"pcm", "raw"}:
        return audio
    if normalized != "wav":
        return None

    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if wav.getsampwidth() != 2:
                return None
            return wav.readframes(wav.getnframes())
    except wave.Error:
        return None
