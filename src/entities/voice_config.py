"""
音色配置实体
"""
import dataclasses
from dataclasses import dataclass, fields
from typing import Union, Optional

from .enums import EmotionType


@dataclass(frozen=True)
class VoiceConfig:
    """
    音色配置实体

    表示 TTS 音色的完整配置

    Attributes:
        voice_id: 音色 ID
        speed: 语速（0.5-2.0）
        volume: 音量（0.1-2.0）
        pitch: 音调（-12 到 +12）
        emotion: 情感

    Example:
        >>> config = VoiceConfig(
        ...     voice_id="male-qn-qingse",
        ...     speed=1.2,
        ...     emotion=EmotionType.HAPPY
        ... )
        >>> config.voice_id
        'male-qn-qingse'
    """

    voice_id: str = "male-qn-qingse"  # 默认音色
    speed: float = 1.0
    volume: float = 1.0
    pitch: int = 0
    emotion: Union[str, EmotionType] = EmotionType.NEUTRAL

    def __post_init__(self):
        """验证逻辑"""
        # 验证音色 ID
        if not self.voice_id or not self.voice_id.strip():
            raise ValueError("音色 ID 不能为空")

        # 验证语速
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError(f"语速必须在 0.5-2.0 之间，当前: {self.speed}")

        # 验证音量
        if not 0.1 <= self.volume <= 2.0:
            raise ValueError(f"音量必须在 0.1-2.0 之间，当前: {self.volume}")

        # 验证音调
        if not -12 <= self.pitch <= 12:
            raise ValueError(f"音调必须在 -12 到 +12 之间，当前: {self.pitch}")

        # 标准化情感参数（支持字符串输入）
        if isinstance(self.emotion, str):
            try:
                object.__setattr__(self, 'emotion', EmotionType(self.emotion))
            except ValueError:
                pass  # 保持字符串

    @classmethod
    def from_dict(cls, data: dict) -> "VoiceConfig":
        """
        从字典创建配置

        使用 dataclasses.fields() 反射获取默认值，确保与类定义同步

        Args:
            data: 配置字典

        Returns:
            VoiceConfig 实例
        """
        # 构建默认值映射
        defaults = {
            f.name: f.default
            for f in fields(cls)
            if f.default is not dataclasses.MISSING
        }

        return cls(
            voice_id=data.get("voice", defaults.get("voice_id", "male-qn-qingse")),
            speed=data.get("speed", defaults.get("speed", 1.0)),
            volume=data.get("volume", defaults.get("volume", 1.0)),
            pitch=data.get("pitch", defaults.get("pitch", 0)),
            emotion=data.get("emotion", defaults.get("emotion", EmotionType.NEUTRAL))
        )

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            配置字典
        """
        emotion_value = self.emotion.value if hasattr(self.emotion, 'value') else self.emotion

        return {
            "voice": self.voice_id,
            "speed": self.speed,
            "volume": self.volume,
            "pitch": self.pitch,
            "emotion": emotion_value
        }
