"""Qwen TTS 引擎 (qwen3-tts-flash)"""
import logging

from voiceforge.entities import EngineResult, TTSRequest
from voiceforge.clients.qwen import QwenClient
from voiceforge.audio.utils import save_audio, estimate_duration

logger = logging.getLogger(__name__)


class QwenTTSEngine:
    """Qwen 专用 TTS 引擎（qwen3-tts-flash）"""

    def __init__(self, api_key: str):
        self.client = QwenClient(api_key)

    def get_engine_name(self) -> str:
        return "qwen_tts"

    def synthesize(self, request: TTSRequest) -> EngineResult:
        try:
            audio_data = self.client.text_to_speech(
                text=request.text, voice=request.voice_id,
            )
            if audio_data is None:
                return EngineResult.fail("Qwen TTS 返回空数据", self.get_engine_name())

            # Qwen 返回 WAV 数据
            save_audio(audio_data, request.output_file, is_wav=True)

            duration = estimate_duration(request.output_file)
            return EngineResult.ok(request.output_file, duration, self.get_engine_name())

        except Exception as e:
            logger.error(f"Qwen TTS 失败: {e}", exc_info=True)
            return EngineResult.fail(str(e), self.get_engine_name())
