"""Audio recorder using PyAudio."""

import struct
import math
import threading
import pyaudio


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


class Recorder:
    """Manages microphone recording with volume tracking."""

    def __init__(self):
        self.recording = False
        self.frames: list[bytes] = []
        self.volume = 0.0
        self._stream = None
        self._pa = None
        self._thread = None

    def start(self):
        if self.recording:
            return
        self.recording = True
        self.frames = []
        self.volume = 0.0
        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def stop(self) -> list[bytes]:
        """Stop recording, return collected frames."""
        if not self.recording:
            return []
        self.recording = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()
        self.volume = 0.0
        return self.frames

    @property
    def duration(self) -> float:
        return len(self.frames) * CHUNK / SAMPLE_RATE

    def _record_loop(self):
        while self.recording:
            try:
                data = self._stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
                self.volume = self._calc_volume(data)
            except Exception:
                break

    @staticmethod
    def _calc_volume(data: bytes) -> float:
        samples = struct.unpack(f"<{len(data) // 2}h", data)
        if not samples:
            return 0.0
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        return min(rms / 5000.0, 1.0)
