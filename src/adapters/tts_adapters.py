"""
TTS 引擎适配器
"""
from pathlib import Path
from typing import Union
import logging

from ..entities import (
    TTSRequest,
    EngineResult,
    EmotionType,
    AudioFormat,
    MiniMaxVoiceID,
    QwenVoiceID,
)
from ..use_cases.tts_use_cases import TTSEngineInterface
from .base_tts_engine import BaseTTSEngine


logger = logging.getLogger(__name__)


class MiniMaxTTSEngine(BaseTTSEngine, TTSEngineInterface):
    """
    MiniMax TTS 引擎适配器

    职责：
    - 实现 TTSEngineInterface
    - 调用 MiniMax API
    - 处理 TTS 合成
    """

    def __init__(
        self,
        api_key: str,
        group_id: str,
        base_url: str = "https://api.minimax.chat",
    ):
        """
        初始化 MiniMax TTS 引擎

        Args:
            api_key: API 密钥
            group_id: 组 ID
            base_url: API 基础 URL
        """
        super().__init__(api_key, base_url)
        self.group_id = group_id

    def get_engine_name(self) -> str:
        """获取引擎名称"""
        return "minimax"

    def synthesize(self, request: TTSRequest) -> EngineResult:
        """
        合成语音

        Args:
            request: TTS 请求

        Returns:
            EngineResult: 合成结果
        """
        try:
            # 1. 构建请求参数
            payload = self._build_payload(request)

            # 2. 调用 API（使用基类方法）
            audio_data = self._call_api(
                endpoint="/v1/text_to_speech",
                payload=payload,
            )

            # 3. 保存文件（使用基类方法）
            self._save_audio_file(audio_data, request.output_file)

            # 4. 返回结果
            duration = self._estimate_duration(audio_data)
            return EngineResult.success(
                file_path=request.output_file,
                duration=duration,
                engine_name=self.get_engine_name(),
            )

        except Exception as e:
            logger.error(f"MiniMax TTS 合成失败: {str(e)}", exc_info=True)
            return EngineResult.failure(
                error_message=f"MiniMax TTS 合成失败: {str(e)}",
                engine_name=self.get_engine_name(),
            )

    def _build_payload(self, request: TTSRequest) -> dict:
        """构建 API 请求参数"""
        return {
            "text": request.text,
            "voice_id": self._normalize_enum_value(request.voice_id),
            "model": "speech-01",
            "speed": request.speed,
            "vol": request.voice_config.volume,
            "pitch": request.voice_config.pitch,
            "emotion": self._normalize_emotion(request.emotion),
            "audio_format": self._normalize_enum_value(request.format),
        }

    def _normalize_emotion(self, emotion: Union[str, EmotionType]) -> str:
        """
        标准化情感参数

        直接使用基类方法，因为 EmotionType 枚举值已经是小写字符串
        """
        return self._normalize_enum_value(emotion)

    def _estimate_duration(self, audio_data: bytes) -> float:
        """
        估算音频时长（MP3 格式）

        Args:
            audio_data: 音频数据

        Returns:
            float: 时长（秒）
        """
        # 简单估算：假设 128kbps MP3
        file_size = len(audio_data)
        bitrate = 128 * 1024 / 8  # bytes per second
        return file_size / bitrate


class QwenOmniTTSEngine(BaseTTSEngine, TTSEngineInterface):
    """
    Qwen Omni TTS 引擎适配器

    职责：
    - 实现 TTSEngineInterface
    - 调用 Qwen API
    - 处理流式音频
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-omni-turbo",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ):
        """
        初始化 Qwen TTS 引擎

        Args:
            api_key: API 密钥
            model: 模型名称
            base_url: API 基础 URL
        """
        super().__init__(api_key, base_url)
        self.model = model

    def get_engine_name(self) -> str:
        """获取引擎名称"""
        return "qwen"

    def synthesize(self, request: TTSRequest) -> EngineResult:
        """
        合成语音

        Args:
            request: TTS 请求

        Returns:
            EngineResult: 合成结果
        """
        try:
            # 1. 构建请求参数
            payload = self._build_payload(request)

            # 2. 调用 API（使用基类方法）
            audio_data = self._call_api(
                endpoint="/audio/speech",
                payload=payload,
            )

            # 3. 添加 WAV 头部（如果需要）
            if str(request.format).lower() == "wav":
                audio_data = self._add_wav_header(audio_data)

            # 4. 保存文件（使用基类方法）
            self._save_audio_file(audio_data, request.output_file)

            # 5. 返回结果
            duration = self._estimate_duration(audio_data)
            return EngineResult.success(
                file_path=request.output_file,
                duration=duration,
                engine_name=self.get_engine_name(),
            )

        except Exception as e:
            logger.error(f"Qwen TTS 合成失败: {str(e)}", exc_info=True)
            return EngineResult.failure(
                error_message=f"Qwen TTS 合成失败: {str(e)}",
                engine_name=self.get_engine_name(),
            )

    def _build_payload(self, request: TTSRequest) -> dict:
        """构建 API 请求参数"""
        return {
            "model": self.model,
            "input": request.text,
            "voice": self._normalize_enum_value(request.voice_id),
            "response_format": "wav",
            "speed": request.speed,
        }

    def _add_wav_header(self, raw_audio: bytes) -> bytes:
        """
        添加 WAV 文件头

        Args:
            raw_audio: 原始音频数据（PCM 格式）

        Returns:
            bytes: 带 WAV 头的音频数据
        """
        # 从 services.audio_utils 导入（已修复循环依赖）
        from services.audio_utils import make_wav_header

        # 16-bit audio: 2 bytes per sample
        num_samples = len(raw_audio) // 2
        wav_header = make_wav_header(num_samples=num_samples, sample_rate=24000)
        return wav_header + raw_audio

    def _estimate_duration(self, audio_data: bytes) -> float:
        """
        估算音频时长（WAV 格式）

        Args:
            audio_data: 音频数据

        Returns:
            float: 时长（秒）
        """
        # WAV 格式：16-bit, 24000Hz, mono
        sample_rate = 24000
        bytes_per_sample = 2
        duration = len(audio_data) / (sample_rate * bytes_per_sample)
        return duration
