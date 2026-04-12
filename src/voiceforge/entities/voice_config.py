"""音色配置实体"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VoiceConfig:
    """音色配置"""
    voice_id: str = "male-qn-qingse"
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0
    emotion: str = "neutral"
