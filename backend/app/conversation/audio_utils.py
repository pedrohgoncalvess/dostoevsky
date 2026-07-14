import io
import wave

import numpy as np


def pcm_to_wav(pcm_data: bytes, sample_rate: int = 24_000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap raw PCM16 bytes in a WAV container."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_data)
    return buffer.getvalue()


def float_to_pcm16(audio: np.ndarray) -> bytes:
    """Convert a float32/float64 numpy audio array to little-endian PCM16 bytes."""
    if audio.size == 0:
        return b""
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)
    return pcm.tobytes()
