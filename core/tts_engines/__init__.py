"""
TTS 引擎模块
"""
from .base import BaseTTSEngine
from .minimax import MiniMaxTTSEngine

__all__ = [
    "BaseTTSEngine",
    "MiniMaxTTSEngine",
]
