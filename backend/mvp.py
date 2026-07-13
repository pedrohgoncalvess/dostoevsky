import os
#!/usr/bin/env python3
"""
Conversational loop: you type → LLM replies via streaming → TTS speaks in real time.

Architecture:
  - Network thread  : fetches PCM chunks from API → puts into queue
  - Playback thread : reads from queue → writes to PyAudio
  - Queue acts as elastic buffer: absorbs network jitter without underruns

Dependencies:
  pip install requests pyaudio
"""

import json
import time
import threading
import queue
import requests
import pyaudio

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
BASE_URL        = "https://openrouter.ai/api/v1"

MODEL           = "hexgrad/kokoro-82m"
VOICE           = "eve"          # grok
VOICE = "tara" #canopy
VOICE = "af_kore" #af_kore
RESPONSE_FORMAT = "pcm"

CHAT_MODEL = "qwen/qwen3.5-flash-02-23"

SYSTEM_PROMPT = (
    "You are a friendly and concise assistant. "
    "Keep replies short and natural for spoken conversation."
)

# ── Audio config ──────────────────────────────────────────────────────────────

PCM_RATE         = 24_000
PCM_CHANNELS     = 1
PCM_FORMAT       = pyaudio.paInt16
BYTES_PER_SAMPLE = 2

HTTP_CHUNK = 2048   # bytes read per network iteration

# How many bytes to accumulate before starting playback (ms → bytes)
# Higher = safer against slow networks, more initial latency
PREBUFFER_MS    = 500
PREBUFFER_BYTES = int(PCM_RATE * BYTES_PER_SAMPLE * PCM_CHANNELS * PREBUFFER_MS / 1000)

# PyAudio callback buffer — small so writes are frequent and smooth
PA_BUFFER = 1024

# If the queue is empty the playback thread waits this long before retrying
QUEUE_TIMEOUT = 0.01   # 10ms

# Sentinel pushed by network thread to signal end of stream
_END = object()

# ── Shared headers ────────────────────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# ── Chat streaming ────────────────────────────────────────────────────────────

def chat_stream(history: list) -> str:
    payload = {
        "model": CHAT_MODEL,
        "stream": True,
        "messages": history,
    }

    full_text = ""
    print("\n\033[94mAssistant:\033[0m ", end="", flush=True)

    with requests.post(
        f"{BASE_URL}/chat/completions",
        headers=HEADERS,
        json=payload,
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if decoded == "data: [DONE]":
                break
            if decoded.startswith("data: "):
                try:
                    chunk = json.loads(decoded[6:])
                    token = chunk["choices"][0]["delta"].get("content", "")
                    if token:
                        print(token, end="", flush=True)
                        full_text += token
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass

    print()
    return full_text

# ── TTS: network thread ───────────────────────────────────────────────────────

def _fetch_audio(text: str, buf: queue.Queue, error_box: list) -> None:
    """Runs in a thread. Fetches PCM chunks and puts them into buf."""
    payload = {
        "model": MODEL,
        "input": text,
        "response_format": RESPONSE_FORMAT,
    }
    if VOICE:
        payload["voice"] = VOICE

    try:
        with requests.post(
            f"{BASE_URL}/audio/speech",
            headers=HEADERS,
            json=payload,
            stream=True,
        ) as resp:
            if resp.status_code != 200:
                try:
                    err = resp.json()
                except Exception:
                    err = resp.text
                error_box.append(f"[TTS ERROR {resp.status_code}] {json.dumps(err, indent=2)}")
                return

            ct = resp.headers.get("Content-Type", "?")
            print(f"\033[90m[content-type: {ct}]\033[0m", end="\r", flush=True)

            for chunk in resp.iter_content(chunk_size=HTTP_CHUNK):
                if chunk:
                    buf.put(chunk)

    except Exception as exc:
        error_box.append(f"[TTS fetch error] {exc}")
    finally:
        buf.put(_END)   # always signal completion

# ── TTS: playback thread ──────────────────────────────────────────────────────

def _play_audio(buf: queue.Queue) -> None:
    """Runs in a thread. Reads from buf and writes to PyAudio."""
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=PCM_FORMAT,
        channels=PCM_CHANNELS,
        rate=PCM_RATE,
        output=True,
        frames_per_buffer=PA_BUFFER,
    )

    try:
        while True:
            try:
                chunk = buf.get(timeout=QUEUE_TIMEOUT)
            except queue.Empty:
                # Network is slower than playback — write silence to avoid underrun
                silence = b"\x00" * PA_BUFFER * BYTES_PER_SAMPLE
                stream.write(silence)
                continue

            if chunk is _END:
                break

            stream.write(chunk)

        # Tail silence: flush PyAudio's hardware buffer before closing
        tail = b"\x00" * int(PCM_RATE * BYTES_PER_SAMPLE * 0.15)  # 150ms
        stream.write(tail)
        time.sleep(0.15)

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

# ── TTS orchestrator ──────────────────────────────────────────────────────────

def tts_stream_play(text: str) -> None:
    if not text.strip():
        return

    buf        = queue.Queue(maxsize=0)   # unbounded — network can run ahead freely
    error_box  = []

    # Start network fetch
    net_thread = threading.Thread(target=_fetch_audio, args=(text, buf, error_box), daemon=True)
    net_thread.start()

    # Pre-buffer: wait until we have enough data before starting playback
    prebuffer_chunks = []
    prebuffer_total  = 0
    print(f"\033[90m[⏳ buffering {PREBUFFER_MS}ms…]\033[0m", end="\r", flush=True)

    while prebuffer_total < PREBUFFER_BYTES:
        try:
            chunk = buf.get(timeout=5.0)
        except queue.Empty:
            break   # timeout — start anyway with what we have

        if chunk is _END:
            # Model returned less data than the pre-buffer target (short reply)
            prebuffer_chunks.append(chunk)
            break

        prebuffer_chunks.append(chunk)
        prebuffer_total += len(chunk)

    if not prebuffer_total:
        if error_box:
            print(f"\n{error_box[0]}")
        else:
            print("\n[TTS] no audio data received")
        net_thread.join()
        return

    # Re-inject pre-buffered chunks at the front of the queue
    # Use a new queue with pre-buffer already loaded so playback starts full
    play_buf = queue.Queue(maxsize=0)
    for c in prebuffer_chunks:
        play_buf.put(c)

    # Forward remaining chunks from net_thread's queue to play_buf as they arrive
    def _forward():
        while True:
            try:
                c = buf.get(timeout=5.0)
            except queue.Empty:
                play_buf.put(_END)
                break
            play_buf.put(c)
            if c is _END:
                break

    fwd_thread = threading.Thread(target=_forward, daemon=True)
    fwd_thread.start()

    print(f"\033[90m[🔊 speaking…]\033[0m", end="\r", flush=True)

    # Playback blocks until _END is consumed
    _play_audio(play_buf)

    fwd_thread.join()
    net_thread.join()

    if error_box:
        print(f"\n{error_box[0]}")

    print(" " * 50, end="\r")

# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("=" * 55)
    print("  Real-time conversational TTS")
    print(f"  Chat model : {CHAT_MODEL}")
    print(f"  TTS model  : {MODEL}" + (f"  ({VOICE})" if VOICE else ""))
    print(f"  Audio      : PCM {PCM_RATE}Hz — PyAudio, no ffmpeg")
    print(f"  Pre-buffer : {PREBUFFER_MS}ms  |  Adaptive jitter fill: on")
    print("  Type 'quit' or Ctrl+C to exit.")
    print("=" * 55)

    while True:
        try:
            user_input = input("\n\033[92mYou:\033[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[exiting]")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit", "bye"}:
            print("[exiting]")
            break

        history.append({"role": "user", "content": user_input})

        assistant_reply = chat_stream(history)
        tts_stream_play(assistant_reply)

        history.append({"role": "assistant", "content": assistant_reply})


if __name__ == "__main__":
    main()