"""Qwen LLM 引擎"""
import logging
from typing import Iterator

from voiceforge.clients.qwen import QwenClient

logger = logging.getLogger(__name__)


class QwenLLMEngine:
    """Qwen LLM 引擎"""

    DEFAULT_MODEL = "qwen3.5-flash"

    def __init__(self, api_key: str, model: str | None = None):
        self.model = model or self.DEFAULT_MODEL
        self.client = QwenClient(api_key)

    def generate(self, prompt: str, *, temperature: float = 0.7,
                 max_tokens: int = 2000) -> str | None:
        return self.client.generate_text(
            prompt=prompt, model=self.model,
            temperature=temperature, max_tokens=max_tokens,
        )

    def generate_stream(self, prompt: str, *, temperature: float = 0.7,
                        max_tokens: int = 2000) -> Iterator[str]:
        return self.client.generate_text_stream(
            prompt=prompt, model=self.model,
            temperature=temperature, max_tokens=max_tokens,
        )

    def is_available(self) -> bool:
        return self.client.api_key is not None
