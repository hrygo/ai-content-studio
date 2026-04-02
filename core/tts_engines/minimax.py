"""
MiniMax TTS 引擎实现
"""
from typing import Optional, Dict, Any
import logging

from .base import BaseTTSEngine
from services.api_client import MiniMaxClient

logger = logging.getLogger(__name__)


class MiniMaxTTSEngine(BaseTTSEngine):
    """MiniMax TTS 引擎"""

    DEFAULT_MODEL = "speech-2.8-hd"
    DEFAULT_VOICE = "male-qn-qingse"

    # 常用音色列表
    COMMON_VOICES = [
        "male-qn-qingse",
        "female-shaonv",
        "male-chunshu",
        "female-yujie",
        "narrator-grand",
        "audiobook_male_2",
        "audiobook_female_2",
        "presenter_male",
        "presenter_female",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        default_voice: Optional[str] = None,
        **kwargs
    ):
        super().__init__(api_key, base_url, **kwargs)
        self.model = model or self.DEFAULT_MODEL
        self.default_voice = default_voice or self.DEFAULT_VOICE
        self.client = MiniMaxClient(api_key, base_url)

    def synthesize(
        self,
        text: str,
        output_file: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: int = 0,
        emotion: str = "neutral",
        english_normalization: bool = False,
        latex_read: bool = False,
        language_boost: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        合成语音

        Args:
            text: 待合成文本
            output_file: 输出文件路径
            voice: 音色 ID
            speed: 语速（0.5-2.0）
            vol: 音量（0.1-2.0）
            pitch: 音调（-12 到 +12）
            emotion: 情感
            english_normalization: 英文数字规范化
            latex_read: LaTeX 公式朗读
            language_boost: 语种增强
            **kwargs: 其他 T2A V2 参数

        Returns:
            成功返回 True，失败返回 False
        """
        audio_bytes = self.client.text_to_speech(
            text=text,
            model=self.model,
            voice_id=voice or self.default_voice,
            speed=speed,
            vol=vol,
            pitch=pitch,
            emotion=emotion,
            english_normalization=english_normalization,
            latex_read=latex_read,
            language_boost=language_boost,
            pronunciation_dict=kwargs.get("pronunciation_dict"),
            voice_modify=kwargs.get("voice_modify"),
            output_format=kwargs.get("output_format", "hex")
        )

        if audio_bytes:
            try:
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
                logger.info(f"音频已保存: {output_file}")
                return True
            except Exception as e:
                logger.error(f"保存音频失败: {e}")
                return False

        return False

    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self.client.api_key is not None

    def get_supported_voices(self) -> list:
        """获取支持的音色列表"""
        return self.COMMON_VOICES.copy()

    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        info = super().get_info()
        info["model"] = self.model
        info["default_voice"] = self.default_voice
        return info
