"""
TTS 用例
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Protocol, Union

from ..entities import (
    TTSRequest,
    EngineResult,
    AudioSegment,
    VoiceConfig,
    TTSEngineType,
    EmotionType,
)
from ..utils import get_fallback_engine
from ..entities.errors import ErrorType

logger = logging.getLogger(__name__)


class TTSEngineInterface(Protocol):
    """TTS 引擎接口（Protocol）"""

    def synthesize(self, request: TTSRequest) -> EngineResult:
        """合成语音"""
        ...

    def get_engine_name(self) -> str:
        """获取引擎名称"""
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
        voice_config: VoiceConfig = None,
        voice_id: str = None,
        speed: float = 1.0,
        volume: float = 1.0,
        pitch: int = 0,
        emotion: Union[str, EmotionType] = "neutral",
        language: str = "auto",
        audio_format: str = "mp3",
    ) -> EngineResult:
        """
        执行 TTS 合成

        Args:
            text: 待合成文本
            output_file: 输出文件路径
            voice_config: 音色配置（优先使用）
            voice_id: 音色 ID（voice_config 为 None 时使用）
            speed: 语速
            volume: 音量
            pitch: 音调
            emotion: 情感
            language: 语言
            audio_format: 音频格式

        Returns:
            EngineResult: 合成结果
        """
        # 构建音色配置（支持传入 VoiceConfig 或单个参数）
        config = voice_config or VoiceConfig(
            voice_id=voice_id or "male-qn-qingse",
            speed=speed,
            volume=volume,
            pitch=pitch,
            emotion=emotion,
        )

        request = TTSRequest(
            text=text,
            output_file=output_file,
            voice_config=config,
            language=language,
            format=audio_format,
        )

        # 调用引擎
        return self.engine.synthesize(request)


@dataclass
class BatchSynthesizeUseCase:
    """
    批量 TTS 合成用例

    职责：
    - 拆分长文本
    - 批量合成
    - 合并音频
    - 支持 fallback 机制

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
    fallback_engine: Optional[TTSEngineInterface] = None  # 备用引擎（可选）

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

        # 1. 批量合成（支持 fallback）
        results: List[EngineResult] = []
        for i, segment in enumerate(segments, 1):
            temp_file = output_file.parent / f"temp_{id(segment)}.mp3"

            # 主引擎合成
            result = self.engine.synthesize(
                TTSRequest(
                    text=segment.text,
                    output_file=temp_file,
                    voice_config=VoiceConfig(voice_id=segment.voice_id),
                )
            )

            # 失败时尝试 fallback
            if not result.success and self._should_fallback(result.error_message):
                result = self._try_fallback(segment, temp_file, i)

            # 仍然失败，返回错误
            if not result.success:
                return result

            results.append(result)

        # 2. 合并音频（如果需要）
        if merge and len(results) > 1:
            audio_files = [r.file_path for r in results]
            merge_result = self.audio_processor.merge_audio_files(
                audio_files, output_file
            )

            # 只在合并成功后清理临时文件
            if merge_result.success:
                for file_path in audio_files:
                    try:
                        file_path.unlink(missing_ok=True)
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {file_path}, 错误: {e}")
            else:
                # 合并失败，保留临时文件以便手动恢复
                logger.warning(
                    f"音频合并失败，临时文件保留在: {[str(f) for f in audio_files]}"
                )

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

    def _should_fallback(self, error_message: str | None) -> bool:
        """判断是否应该切换到备用引擎"""
        if not self.fallback_engine:
            return False

        error_type = ErrorType.classify(error_message)
        return error_type == ErrorType.FALLBACK

    def _try_fallback(
        self, segment: AudioSegment, temp_file: Path, segment_index: int
    ) -> EngineResult:
        """尝试使用 fallback 引擎合成"""
        if not self.fallback_engine:
            return EngineResult.failure("没有配置 fallback 引擎")

        logger.warning(
            f"片段 {segment_index} 主引擎失败，切换到 fallback 引擎: "
            f"{self.fallback_engine.get_engine_name()}"
        )

        try:
            result = self.fallback_engine.synthesize(
                TTSRequest(
                    text=segment.text,
                    output_file=temp_file,
                    voice_config=VoiceConfig(voice_id=segment.voice_id),
                )
            )
            return result
        except Exception as e:
            logger.error(f"Fallback 引擎调用异常: {e}")
            return EngineResult.failure(f"Fallback 引擎失败: {str(e)}")


class AudioProcessorInterface(Protocol):
    """音频处理器接口"""

    def merge_audio_files(
        self,
        audio_files: List[Path],
        output_file: Path,
        pan_list: Optional[List[float]] = None,
        bgm_file: Optional[Path] = None,
        sample_rate: int = 32000,
    ) -> EngineResult:
        """合并音频文件（支持立体声定位和 BGM 混音）"""
        ...
