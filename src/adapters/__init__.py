"""
适配器层（Adapters）- 接口转换器

整洁架构第三层，实现接口适配和外部集成。

特点：
- 将外部框架适配到内部接口
- 实现接口转换
- 处理外部依赖（API、文件系统）
- 可替换性强
"""

from .tts_adapters import (
    MiniMaxTTSEngine,
    QwenOmniTTSEngine,
)
from .audio_adapters import FFmpegAudioProcessor

__all__ = [
    "MiniMaxTTSEngine",
    "QwenOmniTTSEngine",
    "FFmpegAudioProcessor",
]
