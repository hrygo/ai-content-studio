"""
Qwen TTS 引擎实现 (qwen3-tts-flash)
专用语音合成引擎，49种音色 + 8大方言，0.001元/字符
关键：qwen-tts-flash 使用独立 API 端点（非 Chat Completions）
"""
import base64
import json
import logging
import requests
from typing import Optional, List, Dict, Any, Union

from .base import BaseTTSEngine
from src.services.sse_parser import parse_sse_stream
from src.core.enums import QwenVoiceID, LanguageCode

logger = logging.getLogger(__name__)


class QwenTTSEngine(BaseTTSEngine):
    """Qwen TTS 引擎（专用 TTS API）"""

    DEFAULT_MODEL = "qwen3-tts-flash"
    DEFAULT_VOICE = QwenVoiceID.AURORA
    SAMPLE_RATE = 16000

    # 支持的语言（从 LanguageCode 枚举推导）
    SUPPORTED_LANGUAGES = [
        LanguageCode.AUTO,       # 自动检测
        LanguageCode.ZH,         # 中文
        LanguageCode.EN,         # 英文
        LanguageCode.YUE,        # 粤语
        LanguageCode.SHANGHAI,   # 上海话
        LanguageCode.SICHUAN,    # 四川话
        LanguageCode.TIANJIN,    # 天津话
        LanguageCode.WU,         # 吴语
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        default_voice: Optional[Union[str, QwenVoiceID]] = None,
        **kwargs
    ):
        super().__init__(api_key, base_url, **kwargs)
        self.model = model or self.DEFAULT_MODEL
        self.default_voice = self._normalize_voice(default_voice or self.DEFAULT_VOICE)

        # Qwen TTS 使用独立的 API 端点
        if self.base_url:
            # 从 OpenAI 兼容端点转换为原生端点
            self.api_endpoint = self.base_url.replace("/compatible-mode/v1", "").rstrip("/")
        else:
            self.api_endpoint = "https://dashscope.aliyuncs.com"

    def synthesize(
        self,
        text: str,
        output_file: str,
        voice: Optional[Union[str, QwenVoiceID]] = None,
        speed: float = 1.0,
        language: Union[str, LanguageCode] = LanguageCode.AUTO,
        **kwargs
    ) -> bool:
        """
        合成语音

        Args:
            text: 待合成文本
            output_file: 输出文件路径
            voice: 音色 ID（字符串或 QwenVoiceID 枚举）
            speed: 语速
            language: 语言类型（字符串或 LanguageCode 枚举，默认 Auto）
            **kwargs: 其他参数

        Returns:
            成功返回 True，失败返回 False

        Note:
            枚举参数支持字符串输入（向后兼容）：
            - language="zh" → LanguageCode.ZH
        """
        # 标准化枚举参数
        language_normalized = self._normalize_enum(language, LanguageCode)

        audio_bytes = self._synthesize_api(
            text=text,
            voice=voice or self.default_voice,
            speed=speed,
            language=language_normalized
        )

        if audio_bytes:
            try:
                # Qwen TTS 返回 WAV 格式
                import subprocess
                from pathlib import Path

                out_path = Path(output_file)
                if out_path.suffix.lower() == ".mp3":
                    # 先写 WAV，再转 MP3
                    wav_path = out_path.with_suffix(".wav")
                    with open(wav_path, "wb") as f:
                        f.write(audio_bytes)
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", str(wav_path),
                         "-codec:a", "libmp3lame", "-b:a", "128k", str(out_path)],
                        capture_output=True,
                        check=True
                    )
                    wav_path.unlink(missing_ok=True)
                else:
                    with open(out_path, "wb") as f:
                        f.write(audio_bytes)

                logger.info(f"音频已保存: {output_file}")
                return True
            except Exception as e:
                logger.error(f"保存音频失败: {e}")
                return False

        return False

    def _synthesize_api(
        self,
        text: str,
        voice: Union[str, QwenVoiceID],
        speed: float = 1.0,
        language: str = "Auto"
    ) -> Optional[bytes]:
        """
        Qwen TTS API 调用

        Args:
            text: 待合成文本
            voice: 音色 ID（字符串或枚举）
            speed: 语速
            language: 语言类型

        Returns:
            音频字节数据（WAV），失败返回 None
        """
        if not self.api_key:
            logger.error("未配置 DashScope API Key")
            return None

        voice_id = self._normalize_voice(voice).lower()
        language_code = language if language != "Auto" else "Auto"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable"
        }

        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice": voice_id,
                "language_type": language_code
            }
        }

        try:
            # Qwen TTS 使用独立的 API 端点
            url = f"{self.api_endpoint}/api/v1/services/aigc/multimodal-generation/generation"

            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60,
                stream=True
            )

            # 检查状态码
            if resp.status_code != 200:
                logger.error(f"API 请求失败 ({resp.status_code}): {resp.text[:200]}")
                resp.raise_for_status()

            # 使用统一的 SSE 解析器提取音频数据
            audio_chunks = []
            for chunk in parse_sse_stream(resp):
                audio_obj = chunk.get("output", {}).get("audio", {})
                audio_data = audio_obj.get("data")
                if audio_data:
                    audio_chunks.append(audio_data)

            if not audio_chunks:
                logger.error("响应中未包含音频数据")
                return None

            # 分块解码后拼接字节（避免字符串拼接的 O(n²) 复杂度）
            audio_bytes = b"".join(
                base64.b64decode(chunk) for chunk in audio_chunks
            )

            logger.info(f"合成成功 ({len(audio_bytes):,} bytes, {len(text)} chars)")
            return audio_bytes

        except Exception as e:
            logger.error(f"Qwen TTS 调用失败: {e}")
            return None

    def _normalize_voice(self, voice: Union[str, QwenVoiceID]) -> str:
        """
        标准化音色名称（支持字符串和枚举）

        Args:
            voice: 音色字符串或枚举

        Returns:
            音色字符串值
        """
        if isinstance(voice, QwenVoiceID):
            return voice.value
        elif isinstance(voice, str):
            return voice
        return QwenVoiceID.AURORA.value

    def _normalize_enum(self, value: Union[str, Any], enum_class: type) -> str:
        """
        标准化枚举参数（支持字符串和枚举）

        Args:
            value: 字符串或枚举值
            enum_class: 枚举类

        Returns:
            枚举值字符串
        """
        if isinstance(value, str):
            try:
                return enum_class(value).value
            except ValueError:
                logger.warning(f"无效的 {enum_class.__name__} 值: {value}，使用原值")
                return value
        elif hasattr(value, 'value'):
            return value.value
        return value

    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self.api_key is not None

    def get_supported_voices(self) -> list:
        """获取支持的音色列表（字符串格式）"""
        return [voice.value for voice in QwenVoiceID]

    def get_supported_languages(self) -> list:
        """获取支持的语言列表（枚举值）"""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        info = super().get_info()
        info["model"] = self.model
        info["default_voice"] = self.default_voice
        info["sample_rate"] = self.SAMPLE_RATE
        info["supported_languages"] = self.SUPPORTED_LANGUAGES
        return info
