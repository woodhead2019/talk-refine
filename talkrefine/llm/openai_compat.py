"""OpenAI-compatible LLM provider (works with OpenAI, DeepSeek, vLLM, LM Studio, etc.)."""

import requests
from .base import LLMProvider


class OpenAIProvider(LLMProvider):

    def __init__(self, endpoint: str, model: str, api_key: str = "",
                 temperature: float = 0.1, max_tokens: int = 512):
        self._endpoint = endpoint.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return f"OpenAI-compatible ({self._model})"

    def refine(self, raw_text: str, prompt_template: str) -> str:
        prompt = prompt_template.replace("{text}", raw_text)
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            resp = requests.post(
                f"{self._endpoint}/v1/chat/completions",
                headers=headers,
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self._temperature,
                    "max_tokens": self._max_tokens,
                },
                timeout=30,
            )
            resp.raise_for_status()
            choices = resp.json().get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
            return raw_text
        except Exception as e:
            print(f"⚠️  LLM refinement failed ({e}), using raw text")
            return raw_text
