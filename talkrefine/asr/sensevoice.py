"""FunASR SenseVoice engine - optimized for Chinese."""

import re
from .base import ASREngine

# ModelScope -> HuggingFace model ID mapping
_MS_TO_HF = {
    "iic/SenseVoiceSmall": "FunAudioLLM/SenseVoiceSmall",
}


class SenseVoiceEngine(ASREngine):

    def __init__(self, model: str = "FunAudioLLM/SenseVoiceSmall",
                 device: str = "cpu", hub: str = "hf"):
        self._model_name = model
        self._device = device
        self._hub = hub
        self._model = None

    @property
    def name(self) -> str:
        return f"SenseVoice ({self._model_name})"

    def load(self):
        from funasr import AutoModel
        model_id = self._model_name
        # Map legacy ModelScope IDs to HuggingFace when using hf hub
        if self._hub in ("hf", "huggingface") and model_id in _MS_TO_HF:
            model_id = _MS_TO_HF[model_id]
        self._model = AutoModel(
            model=model_id,
            trust_remote_code=False,
            device=self._device,
            disable_update=True,
            hub=self._hub,
        )

    def transcribe(self, audio_path: str, language: str = "auto") -> str:
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        lang = language if language != "auto" else None
        kwargs = {"input": audio_path, "use_itn": True}
        if lang:
            kwargs["language"] = lang
        result = self._model.generate(**kwargs)
        text = result[0]["text"] if result else ""
        return self._clean_tags(text)

    @staticmethod
    def _clean_tags(text: str) -> str:
        """Remove SenseVoice special tags like <|zh|>, <|NEUTRAL|>, etc."""
        return re.sub(r"<\|[^|]*\|>", "", text).strip()
