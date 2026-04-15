"""llama-cpp-python LLM provider — runs model directly in Python, no external service."""

import logging
import os
from pathlib import Path
from .base import LLMProvider

logger = logging.getLogger("talkrefine")

# Default model location
DEFAULT_MODEL_DIR = Path.home() / ".talkrefine" / "models"


class LlamaCppProvider(LLMProvider):

    def __init__(self, model_path: str = "", temperature: float = 0.1,
                 max_tokens: int = 512, n_ctx: int = 2048, n_threads: int = 0):
        self._model_path = model_path
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._n_ctx = n_ctx
        self._n_threads = n_threads or (os.cpu_count() // 2 or 4)
        self._llm = None

    @property
    def name(self) -> str:
        model_name = Path(self._model_path).stem if self._model_path else "not loaded"
        return f"llama.cpp ({model_name})"

    def load(self):
        """Load the GGUF model into memory."""
        from llama_cpp import Llama

        if not self._model_path or not os.path.exists(self._model_path):
            logger.error("Model file not found: %s", self._model_path)
            return

        logger.info("Loading GGUF model: %s", self._model_path)
        self._llm = Llama(
            model_path=self._model_path,
            n_ctx=self._n_ctx,
            n_threads=self._n_threads,
            verbose=False,
        )
        logger.info("GGUF model loaded")

    def unload(self):
        """Release model from memory."""
        if self._llm:
            del self._llm
            self._llm = None
            import gc
            gc.collect()
            logger.info("GGUF model unloaded")

    def warmup(self):
        """Load model if not already loaded."""
        if self._llm is None:
            self.load()

    def refine(self, raw_text: str, prompt_template: str) -> str:
        if self._llm is None:
            logger.warning("LLM not loaded, returning raw text")
            return raw_text

        prompt = prompt_template.replace("{text}", raw_text)
        try:
            output = self._llm(
                prompt,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                stop=["\n\n"],
                echo=False,
            )
            result = output["choices"][0]["text"].strip()
            return result if result else raw_text
        except Exception as e:
            logger.error("LLM refinement failed: %s", e)
            return raw_text
