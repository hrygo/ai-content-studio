"""
AI Content Studio - 专业级 AI 音频内容创作工具

三引擎编排（MiniMax → Qwen TTS → Qwen Omni），通过 LLM 编排播客脚本 + 高保真语音合成。
"""

__version__ = "1.1.0"
__author__ = "AI Content Studio Team"

# 导出核心 API
from src.core.enums import (
    LanguageCode,
    EmotionType,
    MiniMaxVoiceID,
    QwenVoiceID,
    AudioFormat,
    TTSEngineType,
)

from src.core.tts_config import TTSConfig, TTSPresets

__all__ = [
    # Enums
    "LanguageCode",
    "EmotionType",
    "MiniMaxVoiceID",
    "QwenVoiceID",
    "AudioFormat",
    "TTSEngineType",
    # Config
    "TTSConfig",
    "TTSPresets",
]
