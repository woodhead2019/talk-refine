"""Base class for ASR (Automatic Speech Recognition) engines."""

from abc import ABC, abstractmethod


class ASREngine(ABC):
    """Abstract base class for speech recognition engines."""

    @abstractmethod
    def load(self):
        """Load the model. Called once at startup."""
        ...

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "auto") -> str:
        """Transcribe audio file to text.

        Args:
            audio_path: Path to WAV file (16kHz, mono, 16-bit).
            language: Language code ("auto", "zh", "en", etc.)

        Returns:
            Transcribed text string.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable engine name."""
        ...
