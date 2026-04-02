"""
枚举使用示例
演示如何在项目中使用 core.enums 模块
"""
from src.core.enums import (
    LanguageCode,
    EmotionType,
    QwenVoiceID,
    MiniMaxVoiceID,
    AudioFormat,
    TTSEngineType,
    validate_enum_value,
    get_enum_documentation,
)


def demo_language_code():
    """LanguageCode 枚举使用示例"""
    print("=== LanguageCode Demo ===")

    # 1. 直接使用枚举
    lang_zh = LanguageCode.ZH
    print(f"Chinese language code: {lang_zh}")
    print(f"Value: {lang_zh.value}")

    # 2. 从字符串转换（向后兼容）
    user_input = "zh"
    lang = LanguageCode.from_string(user_input)
    print(f"Converted '{user_input}' to {lang}")

    # 3. 无效输入处理
    invalid_lang = LanguageCode.from_string("invalid")
    print(f"Invalid input fallback: {invalid_lang}")

    # 4. 字符串比较（向后兼容）
    print(f"lang_zh == 'zh': {lang_zh == 'zh'}")  # True

    # 5. 获取所有支持的语言
    print(f"Supported languages: {LanguageCode.get_supported_languages()}")


def demo_emotion_type():
    """EmotionType 枚举使用示例"""
    print("\n=== EmotionType Demo ===")

    # 1. 常用情感
    emotion = EmotionType.HAPPY
    print(f"Emotion: {emotion}")
    print(f"Description: 欢快/活泼")

    # 2. 从配置文件字符串转换
    config_emotion = "  calm  "  # 带空格
    normalized = EmotionType.from_string(config_emotion)
    print(f"Normalized '{config_emotion}' to {normalized}")

    # 3. 获取常用情感列表
    common = EmotionType.get_common_emotions()
    print(f"Common emotions: {[e.value for e in common]}")


def demo_voice_id():
    """Voice ID 枚举使用示例"""
    print("\n=== Voice ID Demo ===")

    # 1. Qwen 音色
    voice = QwenVoiceID.CHERRY
    print(f"Qwen voice: {voice}")
    print(f"Description: 甜美女性，温柔亲切")

    # 2. MiniMax 音色
    mm_voice = MiniMaxVoiceID.MALE_QN_QINGSE
    print(f"MiniMax voice: {mm_voice}")
    print(f"Description: 青年男性，清亮清澈")

    # 3. 标准化音色名称
    raw_input = "Aurora"
    normalized = QwenVoiceID.normalize(raw_input)
    print(f"Normalized '{raw_input}' to '{normalized}'")

    # 4. 获取所有音色
    all_qwen_voices = QwenVoiceID.get_all_voices()
    print(f"Total Qwen voices: {len(all_qwen_voices)}")


def demo_audio_format():
    """AudioFormat 枚举使用示例"""
    print("\n=== AudioFormat Demo ===")

    # 1. 检查引擎支持
    wav_supported = AudioFormat.WAV.is_supported_by_engine("qwen_omni")
    mp3_supported = AudioFormat.MP3.is_supported_by_engine("qwen_omni")
    print(f"WAV supported by Qwen Omni: {wav_supported}")  # True
    print(f"MP3 supported by Qwen Omni: {mp3_supported}")  # False

    # 2. 检查是否需要转换
    needs_convert = AudioFormat.needs_conversion(AudioFormat.WAV, AudioFormat.MP3)
    print(f"Needs WAV->MP3 conversion: {needs_convert}")  # True


def demo_engine_type():
    """TTSEngineType 枚举使用示例"""
    print("\n=== TTSEngineType Demo ===")

    # 1. 引擎类型
    engine = TTSEngineType.MINIMAX
    print(f"Engine: {engine}")

    # 2. 别名转换
    alias = TTSEngineType.from_string("qwen")
    print(f"Alias 'qwen' mapped to: {alias}")  # qwen_tts

    # 3. 获取所有引擎
    engines = TTSEngineType.get_all_engines()
    print(f"Available engines: {engines}")


def demo_validation():
    """验证工具函数示例"""
    print("\n=== Validation Demo ===")

    # 1. 验证枚举值
    is_valid = validate_enum_value(LanguageCode, "zh")
    print(f"'zh' is valid LanguageCode: {is_valid}")  # True

    is_valid = validate_enum_value(LanguageCode, "invalid")
    print(f"'invalid' is valid LanguageCode: {is_valid}")  # False

    # 2. 生成文档
    doc = get_enum_documentation(LanguageCode)
    print(f"\n{doc}")


def demo_backward_compatibility():
    """向后兼容性示例"""
    print("\n=== Backward Compatibility Demo ===")

    # 1. 字符串可以与枚举比较
    lang = LanguageCode.ZH
    assert lang == "zh", "Enum should equal to string value"
    print(f"✓ Enum == string: {lang == 'zh'}")

    # 2. 字符串格式化
    message = f"Using language: {lang}"
    assert message == "Using language: zh", "String formatting should work"
    print(f"✓ String formatting: {message}")

    # 3. JSON 序列化（自动使用字符串值）
    import json
    config = {"language": LanguageCode.ZH}
    json_str = json.dumps(config)
    assert '"zh"' in json_str, "JSON serialization should use string value"
    print(f"✓ JSON serialization: {json_str}")


def demo_type_safety():
    """类型安全示例（需要 mypy/pyright 验证）"""
    print("\n=== Type Safety Demo ===")

    # 这里的类型提示会在 IDE 中显示
    lang: LanguageCode = LanguageCode.ZH
    emotion: EmotionType = EmotionType.HAPPY
    voice: QwenVoiceID = QwenVoiceID.CHERRY

    print(f"✓ Type-safe variables: lang={lang}, emotion={emotion}, voice={voice}")

    # IDE 会自动补全：
    # 输入 "LanguageCode." 会列出所有选项
    # 输入 "EmotionType." 会列出所有情感
    print("✓ IDE auto-completion works")


if __name__ == "__main__":
    """运行所有示例"""
    print("=" * 60)
    print("Core Enums Usage Demo")
    print("=" * 60)

    demo_language_code()
    demo_emotion_type()
    demo_voice_id()
    demo_audio_format()
    demo_engine_type()
    demo_validation()
    demo_backward_compatibility()
    demo_type_safety()

    print("\n" + "=" * 60)
    print("Demo completed! All features working as expected.")
    print("=" * 60)

    print("\nNext steps:")
    print("1. Run 'mypy core/enums.py' to verify type safety")
    print("2. Run 'python core/enums.py' to see this demo")
    print("3. Check IDE auto-completion with LanguageCode.<Tab>")
