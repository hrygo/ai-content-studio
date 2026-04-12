"""引擎接口协议"""
from typing import Iterator, Protocol
from pathlib import Path

from voiceforge.entities import EngineResult, TTSRequest


class TTSEngine(Protocol):
    """TTS 引擎接口"""

    def synthesize(self, request: TTSRequest) -> EngineResult: ...
    def get_engine_name(self) -> str: ...


class LLMEngine(Protocol):
    """LLM 引擎接口"""

    def generate(self, prompt: str, *, temperature: float = 0.7,
                 max_tokens: int = 2000) -> str | None: ...
    def generate_stream(self, prompt: str, *, temperature: float = 0.7,
                        max_tokens: int = 2000) -> Iterator[str]: ...
    def is_available(self) -> bool: ...
