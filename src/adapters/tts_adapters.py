"""
TTS 引擎适配器
"""
from pathlib import Path
from typing import Optional, Union
import json

from ..entities import (
    TTSRequest,
    EngineResult,
    EmotionType,
    AudioFormat,
    MiniMaxVoiceID,
    QwenVoiceID,
)
from ..use_cases.tts_use_cases import TTSEngineInterface


class MiniMaxTTSEngine(TTSEngineInterface):
    """
    MiniMax TTS 引擎适配器

    职责：
    - 实现 TTSEngineInterface
    - 调用 MiniMax API
    - 处理 SSE 流式响应
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
        self.api_key = api_key
        self.group_id = group_id
        self.base_url = base_url
        self._client = None  # 延迟初始化

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

            # 2. 调用 API
            audio_data = self._call_api(payload)

            # 3. 保存文件
            request.output_file.parent.mkdir(parents=True, exist_ok=True)
            request.output_file.write_bytes(audio_data)

            # 4. 返回结果
            duration = self._estimate_duration(audio_data)
            return EngineResult.success(
                file_path=request.output_file,
                duration=duration,
                engine_name="minimax",
            )

        except Exception as e:
            return EngineResult.failure(
                error_message=f"MiniMax TTS 合成失败: {str(e)}",
                engine_name="minimax",
            )

    def _build_payload(self, request: TTSRequest) -> dict:
        """构建 API 请求参数"""
        # 转换音色 ID
        voice_id = self._normalize_voice_id(request.voice_id)

        # 转换情感
        emotion = self._normalize_emotion(request.emotion)

        return {
            "text": request.text,
            "voice_id": voice_id,
            "model": "speech-01",
            "speed": request.speed,
            "vol": request.voice_config.volume,
            "pitch": request.voice_config.pitch,
            "emotion": emotion,
            "audio_format": self._normalize_format(request.format),
        }

    def _normalize_voice_id(self, voice_id: str) -> str:
        """标准化音色 ID"""
        # 如果是枚举值，取 value
        if isinstance(voice_id, MiniMaxVoiceID):
            return voice_id.value
        return voice_id

    def _normalize_emotion(self, emotion: Union[str, EmotionType]) -> str:
        """标准化情感参数"""
        if isinstance(emotion, EmotionType):
            # MiniMax 情感映射
            emotion_map = {
                EmotionType.NEUTRAL: "neutral",
                EmotionType.HAPPY: "happy",
                EmotionType.SAD: "sad",
                EmotionType.ANGRY: "angry",
                EmotionType.FEARFUL: "fearful",
            }
            return emotion_map.get(emotion, "neutral")
        return emotion

    def _normalize_format(self, format: Union[str, AudioFormat]) -> str:
        """标准化音频格式"""
        if isinstance(format, AudioFormat):
            format_map = {
                AudioFormat.MP3: "mp3",
                AudioFormat.WAV: "wav",
                AudioFormat.FLAC: "flac",
            }
            return format_map.get(format, "mp3")
        return format

    def _call_api(self, payload: dict) -> bytes:
        """调用 MiniMax API"""
        # 延迟导入避免循环依赖
        import requests

        url = f"{self.base_url}/v1/text_to_speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.content

    def _estimate_duration(self, audio_data: bytes) -> float:
        """估算音频时长"""
        # 简单估算：假设 128kbps MP3
        file_size = len(audio_data)
        bitrate = 128 * 1024 / 8  # bytes per second
        return file_size / bitrate


class QwenOmniTTSEngine(TTSEngineInterface):
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
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

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

            # 2. 调用 API
            audio_data = self._call_api(payload)

            # 3. 保存文件（WAV 格式需要添加头部）
            request.output_file.parent.mkdir(parents=True, exist_ok=True)
            if str(request.format).lower() == "wav":
                audio_data = self._add_wav_header(audio_data)
            request.output_file.write_bytes(audio_data)

            # 4. 返回结果
            duration = self._estimate_duration(audio_data)
            return EngineResult.success(
                file_path=request.output_file,
                duration=duration,
                engine_name="qwen",
            )

        except Exception as e:
            return EngineResult.failure(
                error_message=f"Qwen TTS 合成失败: {str(e)}",
                engine_name="qwen",
            )

    def _build_payload(self, request: TTSRequest) -> dict:
        """构建 API 请求参数"""
        voice_id = self._normalize_voice_id(request.voice_id)

        return {
            "model": self.model,
            "input": request.text,
            "voice": voice_id,
            "response_format": "wav",
            "speed": request.speed,
        }

    def _normalize_voice_id(self, voice_id: str) -> str:
        """标准化音色 ID"""
        if isinstance(voice_id, QwenVoiceID):
            return voice_id.value
        return voice_id

    def _call_api(self, payload: dict) -> bytes:
        """调用 Qwen API"""
        import requests

        url = f"{self.base_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        return response.content

    def _add_wav_header(self, raw_audio: bytes) -> bytes:
        """添加 WAV 文件头"""
        # 从 services.audio_utils 导入（已修复循环依赖）
        from services.audio_utils import make_wav_header

        return make_wav_header(raw_audio)

    def _estimate_duration(self, audio_data: bytes) -> float:
        """估算音频时长"""
        # WAV 格式：16-bit, 24000Hz, mono
        sample_rate = 24000
        bytes_per_sample = 2
        duration = len(audio_data) / (sample_rate * bytes_per_sample)
        return duration
