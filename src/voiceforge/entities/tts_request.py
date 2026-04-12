"""TTS 请求实体"""
from dataclasses import dataclass
from pathlib import Path

from .voice_config import VoiceConfig


@dataclass(frozen=True)
class TTSRequest:
    """TTS 合成请求"""
    text: str
    output_file: Path
    voice_config: VoiceConfig = None

    @property
    def voice_id(self) -> str:
        return self.voice_config.voice_id if self.voice_config else "male-qn-qingse"

    @property
    def speed(self) -> float:
        return self.voice_config.speed if self.voice_config else 1.0

    @property
    def emotion(self) -> str:
        return self.voice_config.emotion if self.voice_config else "neutral"
