"""Use Cases — 业务用例层"""
import logging
from dataclasses import dataclass
from pathlib import Path

from voiceforge.entities import (
    EngineResult, TTSRequest, VoiceConfig, AudioSegment, ErrorType,
)
from voiceforge.protocols.engine import TTSEngine
from voiceforge.protocols.processor import AudioProcessor

logger = logging.getLogger(__name__)


def _try_fallback_synthesize(
    fallback_engine: TTSEngine | None,
    request: TTSRequest,
    idx: int,
) -> EngineResult:
    """统一的 fallback 合成逻辑（Batch / Dialogue 共用）"""
    if not fallback_engine:
        return EngineResult.fail("无 fallback 引擎")
    logger.warning(f"片段 {idx} 主引擎失败，切换 fallback: {fallback_engine.get_engine_name()}")
    try:
        return fallback_engine.synthesize(request)
    except Exception as e:
        return EngineResult.fail(f"Fallback 失败: {e}")


def _should_fallback(fallback_engine: TTSEngine | None, error_message: str | None) -> bool:
    """判断是否应该切换到备用引擎"""
    if not fallback_engine:
        return False
    return ErrorType.classify(error_message) == ErrorType.FALLBACK


@dataclass
class SynthesizeSpeechUseCase:
    """单次 TTS 合成"""

    engine: TTSEngine

    def execute(
        self,
        text: str,
        output_file: Path,
        voice_id: str | None = None,
        speed: float = 1.0,
        emotion: str = "neutral",
    ) -> EngineResult:
        if not text:
            return EngineResult.fail("文本内容为空")

        request = TTSRequest(
            text=text,
            output_file=output_file,
            voice_config=VoiceConfig(
                voice_id=voice_id or "male-qn-qingse",
                speed=speed,
                emotion=emotion,
            ),
        )
        return self.engine.synthesize(request)


@dataclass
class BatchSynthesizeUseCase:
    """批量 TTS 合成（含 fallback）"""

    engine: TTSEngine
    audio_processor: AudioProcessor
    fallback_engine: TTSEngine | None = None

    def execute(
        self, segments: list[AudioSegment], output_file: Path,
    ) -> EngineResult:
        if not segments:
            return EngineResult.fail("音频片段列表不能为空")

        results: list[EngineResult] = []
        for i, segment in enumerate(segments):
            temp_file = output_file.parent / f"_temp_{i}_{output_file.name}"

            request = TTSRequest(
                text=segment.text,
                output_file=temp_file,
                voice_config=VoiceConfig(voice_id=segment.voice_id),
            )
            result = self.engine.synthesize(request)

            if not result.success and _should_fallback(self.fallback_engine, result.error_message):
                result = _try_fallback_synthesize(self.fallback_engine, request, i + 1)

            if not result.success:
                for r in results:
                    if r.file_path:
                        r.file_path.unlink(missing_ok=True)
                return result

            results.append(result)

        if len(results) == 1:
            r = results[0]
            if r.file_path and r.file_path != output_file:
                r.file_path.rename(output_file)
            return EngineResult.ok(output_file, r.duration, r.engine_name)

        audio_files = [r.file_path for r in results if r.file_path]
        merge_result = self.audio_processor.merge_audio_files(audio_files, output_file)

        for f in audio_files:
            f.unlink(missing_ok=True)

        return merge_result
