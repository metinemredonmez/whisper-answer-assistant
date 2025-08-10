#!/usr/bin/env python3
"""
Whisper Answer Assistant (EN focus): Realtime EN transcript + instant EN answer
- Realtime mic listening (WebRTC VAD)
- Transcribe with faster-whisper (auto language; we route if EN)
- If the utterance looks like an English question, ask ChatGPT for a short, speakable answer
- Optionally auto-copy the answer to clipboard (--auto-copy)
- Logs to meeting_log.txt

Usage:
  python whisper_answer_assistant.py --whisper-model base --auto-copy
  python whisper_answer_assistant.py --list-devices
"""

import argparse
import os
import sys
import time
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import sounddevice as sd
import webrtcvad
import pyperclip  # optional auto-copy (safe if not used)
from dotenv import load_dotenv
load_dotenv()

from faster_whisper import WhisperModel
from openai import OpenAI

AUDIO_SR = 16000
CHANNELS = 1
DTYPE = "int16"
FRAME_MS = 20
FRAME_SAMPLES = int(AUDIO_SR * FRAME_MS / 1000)
VAD_AGGRESSIVENESS = 2
MAX_SEGMENT_SEC = 15
SILENCE_FOLLOW_SEC = 0.6

LOG_PATH = "meeting_log.txt"

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(line: str):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)

EN_QUESTION_STARTS = (
    "what", "why", "how", "when", "where", "who", "which",
    "can", "could", "should", "would", "do", "does", "did",
    "is", "are", "am", "will", "may", "might"
)

def is_english_question(text: str, lang: str) -> bool:
    if (lang or "").lower() != "en":
        return False
    t = text.strip().lower()
    if not t:
        return False
    return t.endswith("?") or t.startswith(EN_QUESTION_STARTS)

SYSTEM_PROMPT = (
    "You are a senior engineer joining a live meeting. "
    "When you receive an English question, craft a concise, natural, SPEAKABLE answer "
    "(1–3 sentences). Avoid fluff. If code is needed, give the tiniest working snippet. "
    "Do NOT ask clarifying questions; make reasonable assumptions and proceed."
)

def build_openai():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set. Put it in env or .env")
    return OpenAI()

def stream_answer(client: OpenAI, question: str, model: str = "gpt-4o-mini"):
    return client.chat.completions.create(
        model=model,
        stream=True,
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )

def pcm_float32_from_int16(pcm16: bytes) -> np.ndarray:
    a = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
    return a

@dataclass
class SegState:
    buf: bytearray = field(default_factory=bytearray)
    start: Optional[float] = None
    last_voiced: Optional[float] = None

class Worker(threading.Thread):
    def __init__(self, device: Optional[int], whisper_model: str, auto_copy: bool, openai_model: str):
        super().__init__(daemon=True)
        self.device = device
        self.whisper_model = whisper_model
        self.auto_copy = auto_copy
        self.openai_model = openai_model

        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.seg = SegState()
        self.stop_evt = threading.Event()
        self.model = None
        self.client = None

    def run(self):
        print(f"Loading faster-whisper model: {self.whisper_model} ...")
        self.model = WhisperModel(self.whisper_model, device="auto", compute_type="auto")
        print("Whisper ready.")

        try:
            self.client = build_openai()
        except Exception as e:
            print("⚠️ OpenAI init error:", e)
            print("Continuing without answers (transcript only).")
            self.client = None

        try:
            with sd.RawInputStream(
                samplerate=AUDIO_SR,
                blocksize=FRAME_SAMPLES,
                device=self.device,
                channels=CHANNELS,
                dtype=DTYPE,
            ) as stream:
                print("🎤 Listening... Ctrl+C to stop.")
                while not self.stop_evt.is_set():
                    frame = stream.read(FRAME_SAMPLES)[0]
                    self._process_frame(frame)
        except Exception as e:
            print("Audio error:", e)

    def stop(self):
        self.stop_evt.set()

    def _process_frame(self, frame: bytes):
        if not frame:
            return
        voiced = self.vad.is_speech(frame, AUDIO_SR)
        now = time.time()

        if voiced:
            if self.seg.start is None:
                self.seg.start = now
                self.seg.buf = bytearray()
            self.seg.buf.extend(frame)
            self.seg.last_voiced = now
            if (now - self.seg.start) > MAX_SEGMENT_SEC:
                self._finalize(now, reason="maxlen")
        else:
            if self.seg.start is not None and self.seg.last_voiced is not None:
                if (now - self.seg.last_voiced) >= SILENCE_FOLLOW_SEC:
                    self._finalize(now, reason="silence")

    def _finalize(self, now: float, reason: str):
        pcm16 = bytes(self.seg.buf)
        self.seg = SegState()
        if not pcm16:
            return

        print(f"\n[{ts()}] (segment {reason}) decoding...")
        audio = pcm_float32_from_int16(pcm16)
        try:
            segments, info = self.model.transcribe(
                audio,
                language=None,  # auto
                task="transcribe",
                beam_size=1,
                vad_filter=False,
                word_timestamps=False,
                condition_on_previous_text=False,
            )
            text = " ".join(s.text.strip() for s in segments if s.text)
            lang = getattr(info, "language", None) or "auto"
            prob = getattr(info, "language_probability", None)
        except Exception as e:
            print("Transcription error:", e)
            log(f"[{ts()}] ERROR transcribe: {e}\n")
            return

        if text.strip():
            prob_s = f", p={prob:.2f}" if prob is not None else ""
            print(f"[{ts()}] You ({lang}{prob_s}): {text}")
            log(f"[{ts()}] USER({lang}): {text}\n")

            if is_english_question(text, lang):
                print("-" * 80)
                print(f"🧩 English question detected:\n> {text}")
                log(f"[{ts()}] ROUTER: EN question: {text}\n")
                if self.client is None:
                    print("(OpenAI not configured) Skipping answer.\n" + "-" * 80)
                    return
                try:
                    stream = stream_answer(self.client, text, model=self.openai_model)
                    print("🤖 Suggested answer (speak this):")
                    log(f"[{ts()}] ASSISTANT: ")
                    collected = []
                    for chunk in stream:
                        delta = ""
                        try:
                            delta = chunk.choices[0].delta.get("content", "")
                        except Exception:
                            pass
                        if delta:
                            collected.append(delta)
                            print(delta, end="", flush=True)
                            log(delta)
                    answer = "".join(collected).strip()
                    print("\n" + "-" * 80)
                    log("\n")
                    if self.auto_copy and answer:
                        try:
                            pyperclip.copy(answer)
                            print("📋 Copied to clipboard.")
                        except Exception:
                            pass
                except Exception as e:
                    print("\n⚠️ OpenAI error:", e)
                    log(f"[{ts()}] ERROR OpenAI: {e}\n")

def list_devices_and_exit():
    print(sd.query_devices())
    try:
        print("\nDefault input device index:", sd.default.device[0])
    except Exception:
        pass
    sys.exit(0)

def main():
    p = argparse.ArgumentParser(description="Whisper Answer Assistant (EN focus)")
    p.add_argument("--list-devices", action="store_true", help="List audio devices and exit")
    p.add_argument("--device", type=int, default=None, help="Mic device index")
    p.add_argument("--whisper-model", type=str, default="base",
                   help="tiny|base|small|medium|large-v3 or local path")
    p.add_argument("--auto-copy", action="store_true", help="Copy answer to clipboard automatically")
    p.add_argument("--openai-model", type=str, default="gpt-4o-mini", help="ChatGPT model name")
    args = p.parse_args()

    if args.list_devices:
        list_devices_and_exit()

    print("=" * 80)
    print("🎧 Whisper Answer Assistant")
    print(f"Whisper model: {args.whisper_model}")
    print(f"Mic device: {args.device if args.device is not None else 'default'}")
    print(f"Auto-copy: {'ON' if args.auto_copy else 'OFF'}")
    print("=" * 80)

    worker = Worker(
        device=args.device,
        whisper_model=args.whisper_model,
        auto_copy=args.auto_copy,
        openai_model=args.openai_model,
    )
    try:
        worker.start()
        while worker.is_alive():
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
    finally:
        worker.stop()

if __name__ == "__main__":
    main()
