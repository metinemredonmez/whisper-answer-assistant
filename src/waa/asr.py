# --- src/waa/asr.py ---
import numpy as np
from faster_whisper import WhisperModel

def pcm_float32_from_int16(pcm16: bytes):
    return np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0

class WhisperASR:
    def __init__(self, model_name: str = "base"):
        # device="auto", compute_type="auto" → en hızlı uygun ayar
        self.model = WhisperModel(model_name, device="auto", compute_type="auto")

    def transcribe_segment(self, pcm16: bytes, language=None):
        """Returns: (text, lang, lang_prob)"""
        audio = pcm_float32_from_int16(pcm16)
        segments, info = self.model.transcribe(
            audio,
            language=language,                 # None veya "en"
            task="transcribe",
            beam_size=1,                       # hızlı
            vad_filter=False,
            word_timestamps=False,
            condition_on_previous_text=False,
        )
        text = " ".join(s.text.strip() for s in segments if s.text)
        lang = getattr(info, "language", None) or "auto"
        prob = float(getattr(info, "language_probability", 0.0) or 0.0)
        return text, lang, prob