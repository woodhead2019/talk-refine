"""OpenAI Whisper engine - multilingual support."""

from .base import ASREngine


class WhisperEngine(ASREngine):

    def __init__(self, model: str = "medium", device: str = "cpu"):
        self._model_size = model
        self._device = device
        self._model = None

    @property
    def name(self) -> str:
        return f"Whisper ({self._model_size})"

    def load(self):
        try:
            import whisper
            self._model = whisper.load_model(self._model_size, device=self._device)
        except ImportError:
            raise ImportError(
                "whisper not installed. Run: pip install openai-whisper"
            )

    def transcribe(self, audio_path: str, language: str = "auto") -> str:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        kwargs = {}
        if language != "auto":
            kwargs["language"] = language

        result = self._model.transcribe(audio_path, **kwargs)
        return result.get("text", "").strip()
