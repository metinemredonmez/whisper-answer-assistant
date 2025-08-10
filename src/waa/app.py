# --- src/waa/app.py ---
import time
import pyperclip
import yaml
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

from .audio import MicSegmenter
from .asr import WhisperASR
from .detect import is_english_question, load_keywords, contains_keyword
from .llm import ChatAssistant

load_dotenv()

def run(
    device: Optional[int] = None,
    whisper_model: str = "base",
    config_path: Optional[str] = "configs/settings.yaml",
    keywords_path: Optional[str] = "configs/keywords.en.txt",
):
    # Varsayılanlar
    sr = 16000; frame_ms = 20; vad_aggr = 2; max_seg = 12.0; silence = 0.30
    auto_copy = False; openai_model = "gpt-4o-mini"; require_dev_keyword = False
    min_prob = 0.0; min_chars = 0; force_en = False

    # YAML konfigürasyonu
    if config_path and Path(config_path).exists():
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        sr = cfg.get("audio", {}).get("sample_rate", sr)
        frame_ms = cfg.get("audio", {}).get("frame_ms", frame_ms)
        vad_aggr = cfg.get("audio", {}).get("vad_aggressiveness", vad_aggr)
        max_seg = cfg.get("audio", {}).get("max_segment_sec", max_seg)
        silence = cfg.get("audio", {}).get("silence_follow_sec", silence)

        assistant_cfg = cfg.get("assistant", {}) or {}
        auto_copy = assistant_cfg.get("auto_copy", auto_copy)
        openai_model = assistant_cfg.get("openai_model", openai_model)
        require_dev_keyword = assistant_cfg.get("require_dev_keyword", require_dev_keyword)
        min_prob = float(assistant_cfg.get("min_lang_prob", min_prob) or 0.0)
        min_chars = int(assistant_cfg.get("min_chars", min_chars) or 0)
        force_en = bool(assistant_cfg.get("force_language_en", force_en))
    else:
        cfg = {}

    keywords = load_keywords(keywords_path) if keywords_path else set()

    print("=" * 80)
    print("🎧 Whisper Answer Assistant")
    print("Whisper model:", whisper_model)
    print("Mic device:", device if device is not None else "default")
    print("Auto-copy:", "ON" if auto_copy else "OFF")
    print("Require dev keyword:", "ON" if require_dev_keyword else "OFF")
    print("Min EN prob:", "{:.2f}".format(min_prob))
    print("Min chars:", min_chars)
    print("Force EN:", force_en)
    print("=" * 80)

    seg = MicSegmenter(
        samplerate=sr,
        frame_ms=frame_ms,
        vad_aggressiveness=vad_aggr,
        max_segment_sec=max_seg,
        silence_follow_sec=silence,
        device=device,
    )
    asr = WhisperASR(whisper_model)

    try:
        assistant = ChatAssistant(openai_model)
    except Exception as e:
        print("⚠️ OpenAI init error → sadece transkript:", e)
        assistant = None

    for pcm16, reason in seg.segments():
        print("\n[{0}] (segment {1}) decoding...".format(time.strftime("%Y-%m-%d %H:%M:%S"), reason))
        try:
            text, lang, prob = asr.transcribe_segment(pcm16, language=("en" if force_en else None))
        except Exception as e:
            print("Transcription error:", e)
            continue

        if not text.strip():
            continue

        prob_s = ", p={0:.2f}".format(prob) if prob else ""
        print("[{0}] You ({1}{2}): {3}".format(time.strftime("%Y-%m-%d %H:%M:%S"), lang, prob_s, text))

        if is_english_question(text, lang):
            # Filtreler
            if len(text) < min_chars:
                continue
            if prob and prob < min_prob:
                continue
            if require_dev_keyword and not contains_keyword(text, keywords):
                continue

            print("-" * 80)
            print("🧩 English question detected:\n> {0}".format(text))
            if assistant:
                print("🤖 Suggested answer (speak this):")
                collected = []
                for token in assistant.stream_answer(text):
                    print(token, end="", flush=True)
                    collected.append(token)
                ans = "".join(collected).strip()
                print("\n" + "-" * 80)
                if ans and auto_copy:
                    try:
                        pyperclip.copy(ans)
                        print("📋 Copied to clipboard.")
                    except Exception:
                        pass