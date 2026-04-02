"""
Qwen 引擎使用示例
演示如何使用新架构的 Qwen LLM 和 TTS 引擎
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.llm_engines import QwenLLMEngine
from src.core.tts_engines import QwenOmniTTSEngine, QwenTTSEngine
from src.services.config import get_config


def example_qwen_llm():
    """示例：使用 Qwen LLM 引擎"""
    print("\n=== Qwen LLM 引擎示例 ===\n")

    # 初始化引擎
    engine = QwenLLMEngine(model="qwen-turbo")

    # 检查可用性
    if not engine.is_available():
        print("❌ Qwen LLM 引擎不可用，请配置 QWEN_API_KEY")
        return

    print(f"✅ 引擎信息: {engine.get_info()}")

    # 非流式生成
    print("\n--- 非流式生成 ---")
    prompt = "请用一句话介绍通义千问"
    result = engine.generate(prompt, temperature=0.7, max_tokens=100)
    if result:
        print(f"生成结果: {result}")

    # 流式生成
    print("\n--- 流式生成 ---")
    print("生成中: ", end="", flush=True)
    for chunk in engine.generate_stream(prompt, temperature=0.7, max_tokens=100):
        print(chunk, end="", flush=True)
    print("\n")


def example_qwen_omni_tts():
    """示例：使用 Qwen Omni TTS 引擎"""
    print("\n=== Qwen Omni TTS 引擎示例 ===\n")

    # 初始化引擎
    engine = QwenOmniTTSEngine()

    # 检查可用性
    if not engine.is_available():
        print("❌ Qwen Omni TTS 引擎不可用，请配置 DASHSCOPE_API_KEY")
        return

    print(f"✅ 引擎信息: {engine.get_info()}")

    # 合成语音
    output_file = "examples/output/qwen_omni_demo.wav"
    text = "你好，这是通义千问全模态模型的语音合成测试。"

    print(f"\n正在合成: {text}")
    success = engine.synthesize(
        text=text,
        output_file=output_file,
        voice="cherry",
        system_prompt="You are a friendly assistant."
    )

    if success:
        print(f"✅ 音频已保存: {output_file}")
    else:
        print("❌ 合成失败")


def example_qwen_tts():
    """示例：使用 Qwen TTS 引擎（专用 TTS API）"""
    print("\n=== Qwen TTS 引擎示例 ===\n")

    # 初始化引擎
    engine = QwenTTSEngine()

    # 检查可用性
    if not engine.is_available():
        print("❌ Qwen TTS 引擎不可用，请配置 DASHSCOPE_API_KEY")
        return

    print(f"✅ 引擎信息: {engine.get_info()}")
    print(f"支持的语言: {engine.get_supported_languages()}")

    # 合成语音
    output_file = "examples/output/qwen_tts_demo.mp3"
    text = "欢迎使用通义千问语音合成服务，这里有49种音色可供选择。"

    print(f"\n正在合成: {text}")
    success = engine.synthesize(
        text=text,
        output_file=output_file,
        voice="Aurora",
        language="Auto"
    )

    if success:
        print(f"✅ 音频已保存: {output_file}")
    else:
        print("❌ 合成失败")


def example_with_config():
    """示例：使用配置文件管理引擎"""
    print("\n=== 使用配置文件示例 ===\n")

    # 加载配置
    config = get_config("config.example.json")

    # 检查引擎状态
    print("Qwen 引擎状态:", "可用" if config.is_engine_enabled("qwen") else "不可用")
    print("MiniMax 引擎状态:", "可用" if config.is_engine_enabled("minimax") else "不可用")

    # 使用配置初始化引擎
    qwen_cfg = config.get_engine_config("qwen")
    if qwen_cfg and qwen_cfg.enabled:
        engine = QwenLLMEngine(
            api_key=qwen_cfg.api_key,
            base_url=qwen_cfg.base_url,
            model=qwen_cfg.model
        )
        print(f"\n引擎已就绪: {engine.get_info()}")


def example_multi_voice():
    """示例：多音色合成（使用 Qwen TTS 的49种音色）"""
    print("\n=== 多音色合成示例 ===\n")

    engine = QwenTTSEngine()
    if not engine.is_available():
        print("❌ 引擎不可用")
        return

    # 不同音色示例
    voices_demo = [
        ("Aurora", "这是Aurora的声音"),
        ("Cherry", "这是Cherry的声音"),
        ("Ethan", "这是Ethan的声音"),
    ]

    for voice, text in voices_demo:
        output_file = f"examples/output/qwen_voice_{voice.lower()}.wav"
        print(f"合成 {voice}: {text}")

        success = engine.synthesize(
            text=text,
            output_file=output_file,
            voice=voice
        )

        if success:
            print(f"  ✅ 已保存: {output_file}")
        else:
            print(f"  ❌ 合成失败")


def example_dialect():
    """示例：方言合成（Qwen TTS 支持8大方言）"""
    print("\n=== 方言合成示例 ===\n")

    engine = QwenTTSEngine()
    if not engine.is_available():
        print("❌ 引擎不可用")
        return

    # 方言示例
    dialects_demo = [
        ("zh", "标准中文", "这是标准中文发音"),
        ("yue", "粤语", "这是粤语发音"),
        ("sh", "上海话", "这是上海话发音"),
        ("sichuan", "四川话", "这是四川话发音"),
    ]

    for lang, name, text in dialects_demo:
        output_file = f"examples/output/qwen_dialect_{lang}.wav"
        print(f"合成 {name}: {text}")

        success = engine.synthesize(
            text=text,
            output_file=output_file,
            voice="Aurora",
            language=lang
        )

        if success:
            print(f"  ✅ 已保存: {output_file}")
        else:
            print(f"  ❌ 合成失败")


if __name__ == "__main__":
    # 创建输出目录
    os.makedirs("examples/output", exist_ok=True)

    # 运行示例
    print("=" * 60)
    print("Qwen 引擎完整示例")
    print("=" * 60)

    # LLM 示例
    try:
        example_qwen_llm()
    except Exception as e:
        print(f"❌ LLM 示例失败: {e}")

    # TTS 示例
    try:
        example_qwen_omni_tts()
    except Exception as e:
        print(f"❌ Qwen Omni TTS 示例失败: {e}")

    try:
        example_qwen_tts()
    except Exception as e:
        print(f"❌ Qwen TTS 示例失败: {e}")

    # 配置示例
    try:
        example_with_config()
    except Exception as e:
        print(f"❌ 配置示例失败: {e}")

    # 多音色示例（可选）
    # example_multi_voice()

    # 方言示例（可选）
    # example_dialect()

    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
