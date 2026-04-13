"""No-op LLM provider - returns text as-is."""

from .base import LLMProvider


class NoneProvider(LLMProvider):

    @property
    def name(self) -> str:
        return "None (raw transcription)"

    def refine(self, raw_text: str, prompt_template: str) -> str:
        return raw_text
