"""音频处理器接口"""
from typing import Protocol
from pathlib import Path

from voiceforge.entities import EngineResult


class AudioProcessor(Protocol):
    """音频处理器接口"""

    def merge_audio_files(
        self,
        audio_files: list[Path],
        output_file: Path,
        pan_list: list[float] | None = None,
        bgm_file: Path | None = None,
        sample_rate: int = 32000,
    ) -> EngineResult: ...
