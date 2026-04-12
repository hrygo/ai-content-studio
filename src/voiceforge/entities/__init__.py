"""Entities — 核心业务对象（整洁架构最内层）"""

from .audio_segment import AudioSegment
from .engine_result import EngineResult
from .tts_request import TTSRequest
from .voice_config import VoiceConfig
from .enums import (
    LanguageCode,
    EmotionType,
    AudioFormat,
    TTSEngineType,
    MiniMaxVoiceID,
    QwenVoiceID,
)
from .errors import ErrorType

__all__ = [
    "AudioSegment",
    "EngineResult",
    "TTSRequest",
    "VoiceConfig",
    "LanguageCode",
    "EmotionType",
    "AudioFormat",
    "TTSEngineType",
    "MiniMaxVoiceID",
    "QwenVoiceID",
    "ErrorType",
]
