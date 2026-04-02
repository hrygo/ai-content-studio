"""
MiniMax TTS 引擎实现
支持 TTSConfig 参数对象（v1.1.0+）
"""
from typing import Optional, Dict, Any, Union
import logging

from .base import BaseTTSEngine
from src.services.api_client import MiniMaxClient
from src.core.enums import EmotionType, LanguageCode, MiniMaxVoiceID
from src.core.tts_config import TTSConfig

logger = logging.getLogger(__name__)


class MiniMaxTTSEngine(BaseTTSEngine):
    """MiniMax TTS 引擎"""

    DEFAULT_MODEL = "speech-2.8-hd"
    DEFAULT_VOICE = "male-qn-qingse"

    # 常用音色列表（枚举值）
    COMMON_VOICES = [voice.value for voice in [
        MiniMaxVoiceID.MALE_QN_QINGSE,
        MiniMaxVoiceID.FEMALE_SHAONV,
        MiniMaxVoiceID.MALE_CHUNSHU,
        MiniMaxVoiceID.FEMALE_YUJIE,
        MiniMaxVoiceID.NARRATOR_GRAND,
        MiniMaxVoiceID.AUDIOBOOK_MALE_2,
        MiniMaxVoiceID.AUDIOBOOK_FEMALE_2,
        MiniMaxVoiceID.PRESENTER_MALE,
        MiniMaxVoiceID.PRESENTER_FEMALE,
    ]]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        default_voice: Optional[Union[str, MiniMaxVoiceID]] = None,
        **kwargs
    ):
        super().__init__(api_key, base_url, **kwargs)
        self.model = model or self.DEFAULT_MODEL

        # 标准化 default_voice（支持字符串和枚举）
        if default_voice:
            self.default_voice = self._normalize_voice(default_voice)
        else:
            self.default_voice = self.DEFAULT_VOICE

        self.client = MiniMaxClient(api_key, base_url)

    def synthesize(
        self,
        text: str,
        output_file: str,
        config: Optional[TTSConfig] = None,
        # === 向后兼容参数（v1.0.x） ===
        voice: Optional[Union[str, MiniMaxVoiceID]] = None,
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: int = 0,
        emotion: Union[str, EmotionType] = EmotionType.NEUTRAL,
        english_normalization: bool = False,
        latex_read: bool = False,
        language_boost: Optional[Union[str, LanguageCode]] = None,
        **kwargs
    ) -> bool:
        """
        合成语音

        Args:
            text: 待合成文本
            output_file: 输出文件路径
            config: TTSConfig 配置对象（v1.1.0+，推荐）
            # === 以下参数为向后兼容（v1.0.x） ===
            voice: 音色 ID（字符串或 MiniMaxVoiceID 枚举）
            speed: 语速（0.5-2.0）
            vol: 音量（0.1-2.0）
            pitch: 音调（-12 到 +12）
            emotion: 情感（字符串或 EmotionType 枚举，默认 neutral）
            english_normalization: 英文数字规范化
            latex_read: LaTeX 公式朗读
            language_boost: 语种增强（字符串或 LanguageCode 枚举）
            **kwargs: 其他 T2A V2 参数

        Returns:
            成功返回 True，失败返回 False

        Migration Guide (v1.0.x → v1.1.0):
            # 旧 API（仍然支持）
            engine.synthesize(text, file, voice="male-qn-qingse", speed=1.2)

            # 新 API（推荐）
            from core.tts_config import TTSConfig
            config = TTSConfig(voice="male-qn-qingse", speed=1.2)
            engine.synthesize(text, file, config=config)

        Note:
            所有枚举参数同时支持字符串输入（向后兼容）：
            - emotion="happy" → EmotionType.HAPPY
            - language_boost="zh" → LanguageCode.ZH
        """
        # 优先使用 config 参数（新 API）
        if config:
            params = config.to_dict()
            voice_normalized = params.get("voice", self.default_voice)
            speed_normalized = params.get("speed", 1.0)
            vol_normalized = params.get("volume", 1.0)
            pitch_normalized = params.get("pitch", 0)
            emotion_normalized = params.get("emotion", "neutral")
            language_boost_normalized = params.get("language")
        else:
            # 从显式参数构造（向后兼容）
            voice_normalized = self._normalize_voice(voice) if voice else self.default_voice
            emotion_normalized = self._normalize_enum(emotion, EmotionType)
            language_boost_normalized = (
                self._normalize_enum(language_boost, LanguageCode)
                if language_boost else None
            )
            speed_normalized = speed
            vol_normalized = vol
            pitch_normalized = pitch

        audio_bytes = self.client.text_to_speech(
            text=text,
            model=self.model,
            voice_id=voice_normalized,
            speed=speed_normalized,
            vol=vol_normalized,
            pitch=pitch_normalized,
            emotion=emotion_normalized,
            english_normalization=english_normalization,
            latex_read=latex_read,
            language_boost=language_boost_normalized,
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
        """获取支持的音色列表（字符串格式）"""
        return self.COMMON_VOICES.copy()

    def _normalize_voice(self, voice: Union[str, MiniMaxVoiceID]) -> str:
        """
        标准化音色参数（支持字符串和枚举）

        Args:
            voice: 音色字符串或枚举

        Returns:
            音色字符串值
        """
        if isinstance(voice, MiniMaxVoiceID):
            return voice.value
        return voice

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
            # 尝试转换为枚举（容错处理）
            try:
                return enum_class(value).value
            except ValueError:
                logger.warning(f"无效的 {enum_class.__name__} 值: {value}，使用原值")
                return value
        elif hasattr(value, 'value'):
            return value.value
        return value

    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        info = super().get_info()
        info["model"] = self.model
        info["default_voice"] = self.default_voice
        return info
