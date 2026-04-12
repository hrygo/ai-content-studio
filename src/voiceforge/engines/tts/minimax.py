"""MiniMax TTS 引擎"""
import logging

from voiceforge.entities import EngineResult, TTSRequest
from voiceforge.clients.minimax import MiniMaxClient
from voiceforge.audio.utils import estimate_duration

logger = logging.getLogger(__name__)


class MiniMaxTTSEngine:
    """MiniMax T2A V2 引擎"""

    def __init__(self, api_key: str, group_id: str = "default"):
        self.group_id = group_id
        self.client = MiniMaxClient(api_key)

    def get_engine_name(self) -> str:
        return "minimax"

    def synthesize(self, request: TTSRequest) -> EngineResult:
        try:
            audio_data = self.client.text_to_speech(
                text=request.text,
                voice_id=request.voice_id,
                speed=request.speed,
                emotion=request.emotion,
            )
            if audio_data is None:
                return EngineResult.fail("MiniMax TTS 返回空数据", self.get_engine_name())

            request.output_file.parent.mkdir(parents=True, exist_ok=True)
            request.output_file.write_bytes(audio_data)

            duration = estimate_duration(request.output_file)
            return EngineResult.ok(request.output_file, duration, self.get_engine_name())

        except Exception as e:
            logger.error(f"MiniMax TTS 失败: {e}", exc_info=True)
            return EngineResult.fail(str(e), self.get_engine_name())
