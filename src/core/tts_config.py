"""
TTS 配置数据类
提供类型安全的参数封装，解决参数膨胀问题
"""
from dataclasses import dataclass, field
from typing import Optional, Union, Dict, Any
from src.core.enums import EmotionType, LanguageCode, AudioFormat

@dataclass(frozen=True)
class TTSConfig:
    """
    TTS 合成配置（不可变）

    封装 10+ 个 TTS 参数，提供类型安全和 IDE 自动补全

    Attributes:
        voice: 音色 ID（字符串或枚举）
        speed: 语速（0.5-2.0）
        volume: 音量（0.1-2.0）
        pitch: 音调（-12 到 +12）
        emotion: 情感（枚举或字符串）
        language: 语言代码（枚举或字符串）
        format: 输出格式（枚举或字符串）
        model: 模型 ID（可选）

    Examples:
        >>> config = TTSConfig(voice="male-qn-qingse", speed=1.2)
        >>> config.voice
        'male-qn-qingse'

        >>> from core.enums import EmotionType
        >>> config = TTSConfig(emotion=EmotionType.HAPPY)
        >>> config.emotion
        'happy'

    Note:
        - frozen=True 保证线程安全
        - 所有参数可选（使用默认值）
        - 支持枚举和字符串混合输入（向后兼容）
    """
    # 音色参数
    voice: Optional[str] = None

    # 音频参数
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0

    # 风格参数
    emotion: Union[str, EmotionType] = EmotionType.NEUTRAL
    language: Union[str, LanguageCode] = LanguageCode.AUTO

    # 输出参数
    format: Union[str, AudioFormat] = AudioFormat.MP3
    sample_rate: int = 16000

    # 模型参数
    model: Optional[str] = None

    # 高级参数（透传）
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证参数合法性"""
        # 语速范围验证
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError(f"speed 必须在 0.5-2.0 之间，当前: {self.speed}")

        # 音量范围验证
        if not 0.1 <= self.volume <= 2.0:
            raise ValueError(f"volume 必须在 0.1-2.0 之间，当前: {self.volume}")

        # 音调范围验证
        if not -12 <= self.pitch <= 12:
            raise ValueError(f"pitch 必须在 -12 到 +12 之间，当前: {self.pitch}")

        # 采样率验证
        valid_rates = [8000, 16000, 22050, 24000, 44100, 48000]
        if self.sample_rate not in valid_rates:
            raise ValueError(f"sample_rate 必须是 {valid_rates} 之一，当前: {self.sample_rate}")

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于 API 调用）

        Returns:
            参数字典（过滤 None 值）

        Example:
            >>> config = TTSConfig(voice="male-qn-qingse", speed=1.2)
            >>> config.to_dict()
            {'voice': 'male-qn-qingse', 'speed': 1.2, ...}
        """
        result = {
            "voice": self._normalize_value(self.voice),
            "speed": self.speed,
            "volume": self.volume,
            "pitch": self.pitch,
            "emotion": self._normalize_value(self.emotion),
            "language": self._normalize_value(self.language),
            "format": self._normalize_value(self.format),
            "sample_rate": self.sample_rate,
        }

        # 可选参数
        if self.model:
            result["model"] = self.model

        # 合并额外参数
        result.update(self.extra)

        # 过滤 None 值
        return {k: v for k, v in result.items() if v is not None}

    @staticmethod
    def _normalize_value(value: Any) -> Optional[str]:
        """
        标准化枚举值（支持字符串和枚举）

        Args:
            value: 字符串或枚举

        Returns:
            枚举值字符串，None 返回 None
        """
        if value is None:
            return None
        elif hasattr(value, 'value'):
            return value.value
        else:
            return str(value)

    def merge_with(self, **kwargs) -> "TTSConfig":
        """
        合并配置（创建新实例）

        Args:
            **kwargs: 要覆盖的参数

        Returns:
            新的 TTSConfig 实例

        Example:
            >>> config1 = TTSConfig(speed=1.0)
            >>> config2 = config1.merge_with(speed=1.5, emotion="happy")
            >>> config2.speed
            1.5
        """
        current = self.to_dict()
        current.update(kwargs)
        return TTSConfig(**current)


# 常用配置预设
class TTSPresets:
    """TTS 配置预设"""

    # 标准男声
    MALE_STANDARD = TTSConfig(
        voice="male-qn-qingse",
        speed=1.0,
        emotion=EmotionType.NEUTRAL
    )

    # 标准女声
    FEMALE_STANDARD = TTSConfig(
        voice="female-yujie",
        speed=1.0,
        emotion=EmotionType.NEUTRAL
    )

    # 有声书风格
    AUDIOBOOK = TTSConfig(
        voice="audiobook_male_2",
        speed=0.95,
        emotion=EmotionType.NEUTRAL,
        volume=1.1
    )

    # 新闻播报
    NEWS_BROADCAST = TTSConfig(
        voice="presenter_male",
        speed=1.1,
        emotion=EmotionType.NEUTRAL
    )

    # 快节奏内容
    FAST_PACED = TTSConfig(
        speed=1.5,
        pitch=2
    )

    # 慢速讲解
    SLOW_EXPLANATION = TTSConfig(
        speed=0.8,
        pitch=-1
    )
