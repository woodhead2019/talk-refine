"""Base class for LLM providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM text refinement."""

    @abstractmethod
    def refine(self, raw_text: str, prompt_template: str) -> str:
        """Refine raw transcription using LLM.

        Args:
            raw_text: Raw transcribed text from ASR.
            prompt_template: System prompt / instructions for refinement.

        Returns:
            Refined text.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
