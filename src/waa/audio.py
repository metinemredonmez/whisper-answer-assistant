# --- src/waa/audio.py ---
import time
import sounddevice as sd
import webrtcvad
from typing import Optional

class MicSegmenter:
    """Mic → 20ms frames → VAD → voiced segment üretir."""
    def __init__(
        self,
        samplerate: int = 16000,
        frame_ms: int = 20,
        vad_aggressiveness: int = 2,
        max_segment_sec: float = 12.0,
        silence_follow_sec: float = 0.30,
        device: Optional[int] = None,
    ):
        self.sr = samplerate
        self.frame_samples = int(self.sr * frame_ms / 1000)
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.max_segment_sec = max_segment_sec
        self.silence_follow_sec = silence_follow_sec
        self.device = device
        self._buf = bytearray()
        self._seg_start = None
        self._last_voiced = None

    def frames(self):
        dev_in = self.device if self.device is not None else sd.default.device[0]
        info = sd.query_devices(dev_in)
        if info.get("max_input_channels", 0) < 1:
            raise RuntimeError(f"Selected device {dev_in} has no input channels: {info}")

        with sd.RawInputStream(
            samplerate=self.sr,
            blocksize=self.frame_samples,
            device=dev_in,
            channels=1,
            dtype="int16",
        ) as stream:
            while True:
                yield stream.read(self.frame_samples)[0]

    def segments(self):
        for frame in self.frames():
            now = time.time()
            voiced = self.vad.is_speech(frame, self.sr)
            if voiced:
                if self._seg_start is None:
                    self._seg_start = now
                    self._buf = bytearray()
                self._buf.extend(frame)
                self._last_voiced = now
                if (now - self._seg_start) > self.max_segment_sec:
                    seg = bytes(self._buf)
                    self._reset()
                    if seg:
                        yield seg, "maxlen"
            else:
                if self._seg_start is not None and self._last_voiced is not None:
                    if (now - self._last_voiced) >= self.silence_follow_sec:
                        seg = bytes(self._buf)
                        self._reset()
                        if seg:
                            yield seg, "silence"

    def _reset(self):
        self._buf = bytearray()
        self._seg_start = None
        self._last_voiced = None