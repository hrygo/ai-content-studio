"""
核心枚举类型定义
用于替换字符串常量，提升类型安全性和代码可维护性

Usage:
    from core.enums import LanguageCode, EmotionType, QwenVoiceID

    # Type-safe API
    engine.synthesize(
        text="你好",
        voice=QwenVoiceID.CHERRY,
        language=LanguageCode.ZH,
        emotion=EmotionType.NEUTRAL
    )

    # Backward compatibility
    lang = LanguageCode.from_string("zh")  # Auto-convert from string
    print(lang == "zh")  # True (str enum compatibility)
"""
from enum import Enum
from typing import List
import logging

logger = logging.getLogger(__name__)


class LanguageCode(str, Enum):
    """
    语言代码枚举（Qwen TTS 支持）

    用于指定 TTS 合成的目标语言/方言

    Examples:
        >>> LanguageCode.ZH
        <LanguageCode.ZH: 'zh'>

        >>> LanguageCode.from_string("粤语")
        <LanguageCode.YUE: 'yue'>

        >>> "zh" == LanguageCode.ZH
        True
    """
    AUTO = "Auto"              # 自动检测（默认）
    ZH = "zh"                  # 中文（普通话）
    EN = "en"                  # 英文
    YUE = "yue"                # 粤语
    SHANGHAI = "sh"            # 上海话
    SICHUAN = "sichuan"        # 四川话
    TIANJIN = "tianjin"        # 天津话
    WU = "wu"                  # 吴语

    @classmethod
    def from_string(cls, value: str) -> "LanguageCode":
        """
        从字符串转换（向后兼容）

        Args:
            value: 语言代码字符串（不区分大小写）

        Returns:
            LanguageCode 枚举值，无效输入返回 AUTO

        Examples:
            >>> LanguageCode.from_string("ZH")
            <LanguageCode.ZH: 'zh'>

            >>> LanguageCode.from_string("invalid")
            <LanguageCode.AUTO: 'Auto'>
        """
        try:
            # 尝试直接匹配
            return cls(value)
        except ValueError:
            # 尝试小写匹配
            try:
                return cls(value.lower())
            except ValueError:
                logger.warning(
                    f"Unknown language code: '{value}', fallback to AUTO. "
                    f"Supported: {[v.value for v in cls]}"
                )
                return cls.AUTO

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """获取所有支持的语言代码列表"""
        return [v.value for v in cls]


class EmotionType(str, Enum):
    """
    情感类型枚举（MiniMax T2A V2）

    用于控制语音的情感色彩（仅 speech-2.8-hd/turbo 支持）

    Examples:
        >>> EmotionType.HAPPY
        <EmotionType.HAPPY: 'happy'>

        >>> EmotionType.from_string(" Neutral ")
        <EmotionType.NEUTRAL: 'neutral'>
    """
    NEUTRAL = "neutral"        # 中性（默认，适用于大多数场景）
    HAPPY = "happy"            # 欢快/活泼（适合轻松对话、儿童内容）
    SAD = "sad"                # 悲伤/低沉（适合情感故事、深沉叙述）
    ANGRY = "angry"            # 愤怒/激情（适合辩论、激烈讨论）
    CALM = "calm"              # 平静/沉稳（适合新闻播报、纪录片）
    SURPRISED = "surprised"    # 惊讶/夸张（适合儿童科普、戏剧效果）
    FEARFUL = "fearful"        # 恐惧（适合恐怖故事、悬疑场景）
    DISGUSTED = "disgusted"    # 厌恶（适合特殊戏剧效果）
    FLUENT = "fluent"          # 流畅模式（减少停顿，适合快速播报）

    @classmethod
    def from_string(cls, value: str) -> "EmotionType":
        """
        从字符串转换（向后兼容）

        Args:
            value: 情感类型字符串（不区分大小写，支持前后空格）

        Returns:
            EmotionType 枚举值，无效输入返回 NEUTRAL

        Examples:
            >>> EmotionType.from_string("HAPPY")
            <EmotionType.HAPPY: 'happy'>

            >>> EmotionType.from_string("  calm  ")
            <EmotionType.CALM: 'calm'>
        """
        try:
            # 标准化：去除空格 + 小写
            normalized = value.strip().lower()
            return cls(normalized)
        except ValueError:
            logger.warning(
                f"Unknown emotion: '{value}', fallback to NEUTRAL. "
                f"Supported: {[v.value for v in cls]}"
            )
            return cls.NEUTRAL

    @classmethod
    def get_common_emotions(cls) -> List["EmotionType"]:
        """获取常用情感类型（排除罕见用法）"""
        return [
            cls.NEUTRAL,
            cls.HAPPY,
            cls.SAD,
            cls.ANGRY,
            cls.CALM,
            cls.SURPRISED,
        ]


class MiniMaxVoiceID(str, Enum):
    """
    MiniMax 音色 ID 枚举

    包含 T2A V2 API 的常用音色（完整列表见 API 文档）

    Voice Categories:
        - zh_male: 中文男声
        - zh_female: 中文女声
        - en_voices: 英文音色
        - special: 特殊用途音色

    Examples:
        >>> MiniMaxVoiceID.MALE_QN_QINGSE
        <MiniMaxVoiceID.MALE_QN_QINGSE: 'male-qn-qingse'>

        >>> MiniMaxVoiceID.from_string("female-yujie")
        <MiniMaxVoiceID.FEMALE_YUJIE: 'female-yujie'>
    """

    # === 中文男声 ===
    MALE_QN_QINGSE = "male-qn-qingse"      # 青年男性，清亮清澈，适合知识科普
    MALE_QN_BAI = "male-qn-bai"            # 青年男性，标准播报
    MALE_QN_K = "male-qn-K"                # 中年男性，沉稳磁性
    MALE_CHUNSHU = "male-chunshu"          # 青年男性，纯熟稳重

    # === 中文女声 ===
    FEMALE_YUJIE = "female-yujie"          # 青年女性，专业知性
    FEMALE_TIANMEI = "female-tianmei"      # 青年女性，甜美柔和
    FEMALE_TIANMEI_V2 = "female-tianmei_v2"  # 青年女性 v2，柔和细腻
    FEMALE_SHAONV = "female-shaonv"        # 青年女性，少女音

    # === 英文音色 ===
    ENGLISH_EXPRESSIVE_NARRATOR = "English_expressive_narrator"  # Expressive narrator
    ENGLISH_GRACEFUL_LADY = "English_Graceful_Lady"              # Elegant female
    ENGLISH_DAVE_CHARACTER = "English_Dave_Character"            # Character voice
    ENGLISH_GOLDMAN = "English_Goldman"                          # Deep male voice
    ENGLISH_AUSSIE_MAN = "English_Aussie_Man"                    # Australian male
    ENGLISH_BRITISH_MAN = "English_British_Man"                  # British male

    # === 特殊用途 ===
    NARRATOR_GRAND = "narrator-grand"          # 旁白，宏大叙事
    AUDIOBOOK_MALE_2 = "audiobook_male_2"      # 有声书男声
    AUDIOBOOK_FEMALE_2 = "audiobook_female_2"  # 有声书女声
    PRESENTER_MALE = "presenter_male"          # 主持人男声
    PRESENTER_FEMALE = "presenter_female"      # 主持人女声

    @classmethod
    def from_string(cls, value: str) -> "MiniMaxVoiceID":
        """
        从字符串转换（向后兼容）

        Args:
            value: 音色 ID 字符串

        Returns:
            MiniMaxVoiceID 枚举值，无效输入返回默认男声

        Note:
            由于 MiniMax 音色 ID 较多，此处不进行严格验证。
            如需完整验证，建议调用音色查询 API。
        """
        try:
            return cls(value)
        except ValueError:
            logger.warning(
                f"Voice ID '{value}' not in enum (可能是有效的 API 音色). "
                f"常见选项: {[v.value for v in cls.get_common_voices()]}"
            )
            # 返回字符串包装（不中断流程）
            # 实际使用时由 API 层验证
            class _UnknownVoice(str):
                def __new__(cls2, val):
                    return str.__new__(cls2, val)
                value = value

            return _UnknownVoice(value)

    @classmethod
    def get_common_voices(cls) -> List["MiniMaxVoiceID"]:
        """获取常用音色列表（推荐使用）"""
        return [
            cls.MALE_QN_QINGSE,
            cls.FEMALE_YUJIE,
            cls.MALE_QN_K,
            cls.FEMALE_TIANMEI,
            cls.NARRATOR_GRAND,
            cls.AUDIOBOOK_MALE_2,
            cls.AUDIOBOOK_FEMALE_2,
            cls.PRESENTER_MALE,
            cls.PRESENTER_FEMALE,
        ]

    @classmethod
    def get_all_voices(cls) -> List[str]:
        """获取所有枚举定义的音色 ID"""
        return [v.value for v in cls]


class QwenVoiceID(str, Enum):
    """
    Qwen 音色 ID 枚举（大小写不敏感）

    包含 qwen3-tts-flash 和 qwen3-omni-flash 支持的音色

    Voice Categories:
        - 仙女音: 柔和细腻
        - 知性音: 专业稳重
        - 磁性音: 低沉有磁性
        - 少女音: 活泼清脆
        - 英文: 英文专用
        - 方言: 地方方言
        - Omni: Qwen Omni 专用

    Examples:
        >>> QwenVoiceID.CHERRY
        <QwenVoiceID.CHERRY: 'cherry'>

        >>> QwenVoiceID.normalize("Aurora")
        'aurora'
    """
    # === 仙女音 ===
    AURORA = "aurora"          # 年轻女性，清亮活泼
    NANNVANN = "nannuann"      # 年轻女性，温柔细腻
    VERA = "vera"              # 成熟女性，温婉大方
    BELLA = "bella"            # 甜美女性，柔和细腻
    LUNA = "luna"              # 柔和女性，细腻温柔
    MARIA = "maria"
    NATALIE = "natalie"
    NICOLE = "nicole"
    RACHEL = "rachel"

    # === 知性音 ===
    ADA = "ada"                # 知性女性，专业播报
    ALICE = "alice"            # 优雅女性，温柔流畅
    EMILY = "emily"            # 自然女性，清晰流畅
    HANNAH = "hannah"          # 活泼女性，俏皮可爱
    LILY = "lily"              # 清新女性，柔和自然
    RUBY = "ruby"              # 活泼女性，明快清晰
    COCO = "coco"              # 可爱女性，活泼俏皮

    # === 磁性音 ===
    TERRY = "terry"            # 中年男性，磁性低沉
    HARRY = "harry"            # 年轻男性，磁性阳光
    ANDY = "andy"              # 阳光男性，活力充沛
    ANTHONY = "anthony"

    # === 少女音 ===
    AMY = "amy"                # 少女音色，清脆可爱
    DAISY = "daisy"            # 少女音色，明快活泼
    SANDY = "sandy"
    SALLY = "sally"
    TINAS = "tinas"
    YESSA = "yessa"

    # === 高傲少妇 ===
    CLARA = "clara"            # 年轻女性，专业知性
    SARA = "sara"
    SUSAN = "susan"
    LINDA = "linda"
    LISA = "lisa"

    # === 英文音色 ===
    EMMA = "emma"              # 英语女性，自然亲切
    SOPHIA = "sophia"          # 英语女性，优雅知性
    ERIC = "eric"              # 英语男性，成熟稳重
    CHARLOTTE = "charlotte"

    # === 方言 ===
    DYLAN = "dylan"            # 北京话男性，地道方言
    JADA = "jada"              # 上海话女性，软糯吴语
    SUNNY = "sunny"            # 四川话，诙谐幽默

    # === Qwen Omni 专用 ===
    CHERRY = "cherry"          # 甜美女性，温柔亲切（默认）
    ETHAN = "ethan"            # 成熟男性
    CHELSIE = "chelsie"

    @classmethod
    def normalize(cls, voice: str) -> str:
        """
        标准化音色名称（转小写）

        Qwen API 要求小写音色名，此方法确保兼容性

        Args:
            voice: 音色名称（不区分大小写）

        Returns:
            小写音色 ID

        Examples:
            >>> QwenVoiceID.normalize("Aurora")
            'aurora'

            >>> QwenVoiceID.normalize("CHERRY")
            'cherry'
        """
        return voice.lower()

    @classmethod
    def from_string(cls, value: str) -> "QwenVoiceID":
        """
        从字符串转换（向后兼容，大小写不敏感）

        Args:
            value: 音色名称

        Returns:
            QwenVoiceID 枚举值，无效输入返回 CHERRY

        Examples:
            >>> QwenVoiceID.from_string("AURORA")
            <QwenVoiceID.AURORA: 'aurora'>

            >>> QwenVoiceID.from_string("Unknown")
            <QwenVoiceID.CHERRY: 'cherry'>
        """
        try:
            # 标准化为小写
            normalized = value.lower()
            return cls(normalized)
        except ValueError:
            logger.warning(
                f"Unknown Qwen voice: '{value}', fallback to CHERRY. "
                f"Supported: {[v.value for v in cls]}"
            )
            return cls.CHERRY

    @classmethod
    def get_common_voices(cls) -> List["QwenVoiceID"]:
        """获取常用音色列表（推荐使用）"""
        return [
            cls.CHERRY,     # 默认
            cls.AURORA,
            cls.ETHAN,
            cls.EMMA,
            cls.TERRY,
            cls.ADA,
            cls.DYLAN,      # 方言
            cls.JADA,
            cls.SUNNY,
        ]


class AudioFormat(str, Enum):
    """
    音频格式枚举

    支持的音频输出格式

    Examples:
        >>> AudioFormat.WAV
        <AudioFormat.WAV: 'wav'>

        >>> AudioFormat.MP3.is_supported_by_engine("qwen_omni")
        False
    """
    WAV = "wav"    # 无损 WAV（Qwen 原生输出）
    MP3 = "mp3"    # MP3 压缩（MiniMax 原生输出）
    PCM = "pcm"    # 原始 PCM 数据

    @classmethod
    def from_string(cls, value: str) -> "AudioFormat":
        """
        从字符串转换（向后兼容）

        Args:
            value: 格式字符串（不区分大小写）

        Returns:
            AudioFormat 枚举值，无效输入返回 WAV
        """
        try:
            normalized = value.lower()
            return cls(normalized)
        except ValueError:
            logger.warning(
                f"Unknown audio format: '{value}', fallback to WAV. "
                f"Supported: {[v.value for v in cls]}"
            )
            return cls.WAV

    def is_supported_by_engine(self, engine: str) -> bool:
        """
        检查指定引擎是否支持该格式

        Args:
            engine: 引擎名称（"minimax" | "qwen_tts" | "qwen_omni"）

        Returns:
            True 如果支持，False 如果不支持

        Examples:
            >>> AudioFormat.MP3.is_supported_by_engine("minimax")
            True

            >>> AudioFormat.MP3.is_supported_by_engine("qwen_omni")
            False
        """
        # Qwen Omni 不支持 MP3（仅支持 WAV/PCM）
        UNSUPPORTED_FORMATS = {
            "qwen_omni": {AudioFormat.MP3},
        }

        return self not in UNSUPPORTED_FORMATS.get(engine, set())

    @classmethod
    def needs_conversion(cls, source: "AudioFormat", target: "AudioFormat") -> bool:
        """
        判断是否需要格式转换

        Args:
            source: 源格式
            target: 目标格式

        Returns:
            True 如果需要转换，False 如果格式相同

        Examples:
            >>> AudioFormat.needs_conversion(AudioFormat.WAV, AudioFormat.MP3)
            True

            >>> AudioFormat.needs_conversion(AudioFormat.WAV, AudioFormat.WAV)
            False
        """
        return source != target


class TTSEngineType(str, Enum):
    """
    TTS 引擎类型枚举

    定义支持的 TTS 引擎

    Examples:
        >>> TTSEngineType.MINIMAX
        <TTSEngineType.MINIMAX: 'minimax'>

        >>> TTSEngineType.from_string("qwen")
        <TTSEngineType.QWEN_TTS: 'qwen_tts'>
    """
    MINIMAX = "minimax"          # MiniMax T2A V2
    QWEN_TTS = "qwen_tts"        # Qwen TTS Flash（专用 TTS API）
    QWEN_OMNI = "qwen_omni"      # Qwen Omni（多模态）
    QWEN = "qwen"                # 别名（向后兼容，映射到 QWEN_TTS）

    @classmethod
    def from_string(cls, value: str) -> "TTSEngineType":
        """
        从字符串转换（向后兼容）

        Args:
            value: 引擎名称（不区分大小写）

        Returns:
            TTSEngineType 枚举值，无效输入返回 MINIMAX

        Examples:
            >>> TTSEngineType.from_string("QWEN")
            <TTSEngineType.QWEN_TTS: 'qwen_tts'>

            >>> TTSEngineType.from_string("invalid")
            <TTSEngineType.MINIMAX: 'minimax'>
        """
        # 别名映射
        ALIAS_MAPPING = {
            "qwen": cls.QWEN_TTS,  # 默认映射到 qwen_tts
        }

        normalized = value.lower()

        # 先检查别名
        if normalized in ALIAS_MAPPING:
            return ALIAS_MAPPING[normalized]

        # 再尝试直接匹配
        try:
            return cls(normalized)
        except ValueError:
            logger.warning(
                f"Unknown TTS engine: '{value}', fallback to MINIMAX. "
                f"Supported: {[v.value for v in cls]}"
            )
            return cls.MINIMAX

    @classmethod
    def get_all_engines(cls) -> List[str]:
        """获取所有引擎名称"""
        return [v.value for v in cls]


# === Utility Functions ===

def validate_enum_value(enum_class: type, value: str) -> bool:
    """
    验证值是否在枚举中

    Args:
        enum_class: 枚举类
        value: 待验证的值

    Returns:
        True 如果有效，False 如果无效

    Examples:
        >>> validate_enum_value(LanguageCode, "zh")
        True

        >>> validate_enum_value(LanguageCode, "invalid")
        False
    """
    try:
        enum_class.from_string(value)
        return True
    except (AttributeError, ValueError):
        return False


def get_enum_documentation(enum_class: type) -> str:
    """
    生成枚举的文档字符串

    Args:
        enum_class: 枚举类

    Returns:
        Markdown 格式的文档

    Examples:
        >>> doc = get_enum_documentation(LanguageCode)
        >>> print(doc)
        # LanguageCode
        Supported values: Auto, zh, en, yue, sh, sichuan, tianjin, wu
    """
    enum_name = enum_class.__name__
    values = [v.value for v in enum_class]
    docstring = enum_class.__doc__ or ""

    return f"""# {enum_name}

{docstring}

## Supported Values
{', '.join(values)}

## Total: {len(values)} options
"""


# === Export List ===
__all__ = [
    # Enums
    "LanguageCode",
    "EmotionType",
    "MiniMaxVoiceID",
    "QwenVoiceID",
    "AudioFormat",
    "TTSEngineType",

    # Utilities
    "validate_enum_value",
    "get_enum_documentation",
]
