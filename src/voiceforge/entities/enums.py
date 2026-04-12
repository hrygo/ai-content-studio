"""核心枚举类型"""
from enum import Enum
from typing import List
import logging

logger = logging.getLogger(__name__)


class LanguageCode(str, Enum):
    """语言代码（Qwen TTS 方言支持）"""
    AUTO = "Auto"
    ZH = "zh"
    EN = "en"
    YUE = "yue"
    SHANGHAI = "sh"
    SICHUAN = "sichuan"
    TIANJIN = "tianjin"
    WU = "wu"

    @classmethod
    def from_string(cls, value: str) -> "LanguageCode":
        try:
            return cls(value)
        except ValueError:
            try:
                return cls(value.lower())
            except ValueError:
                logger.warning(f"Unknown language code: '{value}', fallback to AUTO")
                return cls.AUTO


class EmotionType(str, Enum):
    """情感类型（MiniMax T2A V2）"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    CALM = "calm"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    FLUENT = "fluent"

    @classmethod
    def from_string(cls, value: str) -> "EmotionType":
        try:
            return cls(value.strip().lower())
        except ValueError:
            logger.warning(f"Unknown emotion: '{value}', fallback to NEUTRAL")
            return cls.NEUTRAL


class MiniMaxVoiceID(str, Enum):
    """MiniMax 音色 ID"""
    # 中文男声
    MALE_QN_QINGSE = "male-qn-qingse"
    MALE_QN_BAI = "male-qn-bai"
    MALE_QN_K = "male-qn-K"
    MALE_CHUNSHU = "male-chunshu"
    # 中文女声
    FEMALE_YUJIE = "female-yujie"
    FEMALE_TIANMEI = "female-tianmei"
    FEMALE_TIANMEI_V2 = "female-tianmei_v2"
    FEMALE_SHAONV = "female-shaonv"
    # 英文音色
    EN_NARRATOR = "English_expressive_narrator"
    EN_GRACEFUL = "English_Graceful_Lady"
    EN_DAVE = "English_Dave_Character"
    EN_GOLDMAN = "English_Goldman"
    # 特殊用途
    NARRATOR_GRAND = "narrator-grand"
    AUDIOBOOK_MALE = "audiobook_male_2"
    AUDIOBOOK_FEMALE = "audiobook_female_2"
    PRESENTER_MALE = "presenter_male"
    PRESENTER_FEMALE = "presenter_female"

    @classmethod
    def from_string(cls, value: str) -> "MiniMaxVoiceID":
        try:
            return cls(value)
        except ValueError:
            logger.warning(f"Voice ID '{value}' not in enum, using as-is")
            return value  # type: ignore[return-value]


class QwenVoiceID(str, Enum):
    """Qwen 音色 ID（大小写不敏感）"""
    # 仙女音
    AURORA = "aurora"
    NANNVANN = "nannuann"
    VERA = "vera"
    BELLA = "bella"
    LUNA = "luna"
    # 知性音
    ADA = "ada"
    ALICE = "alice"
    EMILY = "emily"
    # 磁性音
    TERRY = "terry"
    HARRY = "harry"
    ANDY = "andy"
    # 少女音
    AMY = "amy"
    DAISY = "daisy"
    # 英文
    EMMA = "emma"
    SOPHIA = "sophia"
    ERIC = "eric"
    # 方言
    DYLAN = "dylan"
    JADA = "jada"
    SUNNY = "sunny"
    # Omni 专用
    CHERRY = "cherry"
    ETHAN = "ethan"
    CHELSIE = "chelsie"

    @classmethod
    def from_string(cls, value: str) -> "QwenVoiceID":
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown Qwen voice: '{value}', fallback to CHERRY")
            return cls.CHERRY

    @classmethod
    def common(cls) -> List["QwenVoiceID"]:
        return [cls.CHERRY, cls.AURORA, cls.ETHAN, cls.EMMA, cls.TERRY, cls.ADA]


class AudioFormat(str, Enum):
    """音频格式"""
    WAV = "wav"
    MP3 = "mp3"
    PCM = "pcm"

    @classmethod
    def from_string(cls, value: str) -> "AudioFormat":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.MP3


class TTSEngineType(str, Enum):
    """TTS 引擎类型"""
    MINIMAX = "minimax"
    QWEN_TTS = "qwen_tts"
    QWEN_OMNI = "qwen_omni"
    QWEN = "qwen"  # 别名 → qwen_tts

    @classmethod
    def from_string(cls, value: str) -> "TTSEngineType":
        normalized = value.lower()
        if normalized == "qwen":
            return cls.QWEN_TTS
        try:
            return cls(normalized)
        except ValueError:
            return cls.MINIMAX

    def resolve(self) -> "TTSEngineType":
        """解析别名"""
        return self.QWEN_TTS if self == self.QWEN else self
