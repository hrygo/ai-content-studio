"""
TTS 用例
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Protocol

from ..entities import (
    TTSRequest,
    EngineResult,
    AudioSegment,
    VoiceConfig,
    TTSEngineType,
)


class TTSEngineInterface(Protocol):
    """TTS 引擎接口（Protocol）"""

    def synthesize(self, request: TTSRequest) -> EngineResult:
        """合成语音"""
        ...


@dataclass
class SynthesizeSpeechUseCase:
    """
    单个 TTS 合成用例

    职责：
    - 验证输入
    - 调用 TTS 引擎
    - 返回结果

    Example:
        >>> use_case = SynthesizeSpeechUseCase(engine=qwen_engine)
        >>> result = use_case.execute(
        ...     text="大家好",
        ...     output_file=Path("output.mp3"),
        ...     voice_id="male-qn-qingse"
        ... )
        >>> result.success
        True
    """

    engine: TTSEngineInterface

    def execute(
        self,
        text: str,
        output_file: Path,
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        volume: float = 1.0,
        pitch: int = 0,
        emotion: str = "neutral",
        language: str = "auto",
        audio_format: str = "mp3",
    ) -> EngineResult:
        """
        执行 TTS 合成

        Args:
            text: 待合成文本
            output_file: 输出文件路径
            voice_id: 音色 ID
            speed: 语速
            volume: 音量
            pitch: 音调
            emotion: 情感
            language: 语言
            audio_format: 音频格式

        Returns:
            EngineResult: 合成结果
        """
        # 1. 构建实体
        voice_config = VoiceConfig(
            voice_id=voice_id,
            speed=speed,
            volume=volume,
            pitch=pitch,
            emotion=emotion,
        )

        request = TTSRequest(
            text=text,
            output_file=output_file,
            voice_config=voice_config,
            language=language,
            format=audio_format,
        )

        # 2. 调用引擎
        return self.engine.synthesize(request)


@dataclass
class BatchSynthesizeUseCase:
    """
    批量 TTS 合成用例

    职责：
    - 拆分长文本
    - 批量合成
    - 合并音频

    Example:
        >>> use_case = BatchSynthesizeUseCase(engine=minimax_engine)
        >>> segments = [
        ...     AudioSegment(text="第一段", voice_id="male-qn-qingse"),
        ...     AudioSegment(text="第二段", voice_id="male-qn-jingpin"),
        ... ]
        >>> result = use_case.execute(segments, output_file=Path("output.mp3"))
        >>> result.success
        True
    """

    engine: TTSEngineInterface
    audio_processor: "AudioProcessorInterface"

    def execute(
        self,
        segments: List[AudioSegment],
        output_file: Path,
        merge: bool = True,
    ) -> EngineResult:
        """
        执行批量合成

        Args:
            segments: 音频片段列表
            output_file: 输出文件路径
            merge: 是否合并为一个文件

        Returns:
            EngineResult: 合成结果
        """
        if not segments:
            return EngineResult.failure("音频片段列表不能为空")

        # 1. 批量合成
        results: List[EngineResult] = []
        for segment in segments:
            temp_file = output_file.parent / f"temp_{id(segment)}.mp3"

            result = self.engine.synthesize(
                TTSRequest(
                    text=segment.text,
                    output_file=temp_file,
                    voice_config=VoiceConfig(voice_id=segment.voice_id),
                )
            )

            if not result.success:
                return result

            results.append(result)

        # 2. 合并音频（如果需要）
        if merge and len(results) > 1:
            audio_files = [r.file_path for r in results]
            merge_result = self.audio_processor.merge_audio_files(
                audio_files, output_file
            )

            # 清理临时文件
            for file_path in audio_files:
                file_path.unlink(missing_ok=True)

            return merge_result

        # 3. 单文件直接返回
        if len(results) == 1:
            result = results[0]
            # 重命名到目标路径
            result.file_path.rename(output_file)
            return EngineResult.success(
                file_path=output_file,
                duration=result.duration,
                engine_name=result.engine_name,
            )

        # 4. 多文件不合并（返回第一个）
        return results[0]


class AudioProcessorInterface(Protocol):
    """音频处理器接口"""

    def merge_audio_files(
        self, audio_files: List[Path], output_file: Path
    ) -> EngineResult:
        """合并音频文件"""
        ...
