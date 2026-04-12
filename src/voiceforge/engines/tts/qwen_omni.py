"""Qwen Omni TTS 引擎 (qwen-omni-turbo)"""
import base64
import json
import logging

from voiceforge.entities import EngineResult, TTSRequest
from voiceforge.clients.qwen import QwenClient
from voiceforge.audio.utils import save_audio, estimate_duration, make_wav_header

logger = logging.getLogger(__name__)


class QwenOmniTTSEngine:
    """Qwen Omni 多模态引擎（流式 API）"""

    def __init__(self, api_key: str, base_url: str | None = None):
        self.client = QwenClient(api_key, base_url)

    def get_engine_name(self) -> str:
        return "qwen_omni"

    def synthesize(self, request: TTSRequest) -> EngineResult:
        try:
            pcm_data = self._call_omni_api(request.text, request.voice_id)
            if pcm_data is None:
                return EngineResult.fail("Qwen Omni 返回空数据", self.get_engine_name())

            # Omni 输出裸 PCM → 加 WAV 头
            wav_data = make_wav_header(pcm_data)
            save_audio(wav_data, request.output_file, is_wav=True)

            duration = estimate_duration(request.output_file)
            return EngineResult.ok(request.output_file, duration, self.get_engine_name())

        except Exception as e:
            logger.error(f"Qwen Omni TTS 失败: {e}", exc_info=True)
            return EngineResult.fail(str(e), self.get_engine_name())

    def _call_omni_api(self, text: str, voice: str) -> bytes | None:
        """流式调用 Qwen Omni，收集音频 PCM"""
        url = f"{self.client.base_url}/chat/completions"
        payload = {
            "model": "qwen-omni-turbo",
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "modalities": ["text", "audio"],
            "audio": {"voice": voice.lower(), "format": "wav"},
            "stream": True,
        }

        audio_chunks = bytearray()
        try:
            resp = self.client.session.post(
                url, headers=self.client._headers(), json=payload,
                stream=True, timeout=60,
            )
            for line in resp.iter_lines():
                if not line or not line.startswith(b"data:"):
                    continue
                data_str = line.decode("utf-8")[5:].strip()
                if data_str == "[DONE]":
                    break
                chunk = json.loads(data_str)
                for choice in chunk.get("choices", []):
                    audio_b64 = choice.get("delta", {}).get("audio", "")
                    if audio_b64:
                        audio_chunks.extend(base64.b64decode(audio_b64))

            return bytes(audio_chunks) if audio_chunks else None
        except Exception as e:
            logger.error(f"Qwen Omni API 调用失败: {e}")
            return None
