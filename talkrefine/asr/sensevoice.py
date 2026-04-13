"""FunASR SenseVoice engine - optimized for Chinese."""

import re
from .base import ASREngine


class SenseVoiceEngine(ASREngine):

    def __init__(self, model: str = "iic/SenseVoiceSmall", device: str = "cpu"):
        self._model_name = model
        self._device = device
        self._model = None

    @property
    def name(self) -> str:
        return f"SenseVoice ({self._model_name})"

    def load(self):
        from funasr import AutoModel
        self._model = AutoModel(
            model=self._model_name,
            trust_remote_code=True,
            device=self._device,
            disable_update=True,
        )

    def transcribe(self, audio_path: str, language: str = "auto") -> str:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        lang = language if language != "auto" else "zh"
        result = self._model.generate(input=audio_path, language=lang, use_itn=True)
        text = result[0]["text"] if result else ""
        return self._clean_tags(text)

    @staticmethod
    def _clean_tags(text: str) -> str:
        """Remove SenseVoice special tags like <|zh|>, <|NEUTRAL|>, etc."""
        return re.sub(r"<\|[^|]*\|>", "", text).strip()
