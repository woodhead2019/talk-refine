"""Ollama LLM provider."""

import requests
from .base import LLMProvider


class OllamaProvider(LLMProvider):

    def __init__(self, endpoint: str, model: str, temperature: float = 0.1,
                 max_tokens: int = 512):
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"

    def warmup(self):
        """Pre-load model into memory with long keep_alive."""
        try:
            requests.post(
                f"{self._endpoint}/api/generate",
                json={
                    "model": self._model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": "24h",
                },
                timeout=60,
            )
        except Exception:
            pass

    def refine(self, raw_text: str, prompt_template: str) -> str:
        prompt = prompt_template.replace("{text}", raw_text)
        try:
            resp = requests.post(
                f"{self._endpoint}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "think": False,
                    "keep_alive": "24h",
                    "options": {
                        "temperature": self._temperature,
                        "num_predict": self._max_tokens,
                    },
                },
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json().get("response", "").strip()
            return result if result else raw_text
        except Exception as e:
            print(f"⚠️  LLM refinement failed ({e}), using raw text")
            return raw_text
