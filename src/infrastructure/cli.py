"""
AI Content Studio - 统一命令行工具
Clean Architecture 架构，支持 4 个子命令

用法：
    ai-studio synthesize --source TEXT -o OUTPUT [--engine ENGINE]
    ai-studio dialogue --source FILE -o OUTPUT [--engine ENGINE]
    ai-studio studio --topic TEXT -o OUTPUT [--llm LLM] [--tts TTS]
    ai-studio batch --segments "text1|voice1,text2|voice2" -o OUTPUT [--engine ENGINE]
"""
import argparse
import logging
import sys
from pathlib import Path

from ..entities import TTSEngineType, EmotionType, AudioFormat, MiniMaxVoiceID, AudioSegment
from ..infrastructure.container import Container

logger = logging.getLogger(__name__)


def _resolve_source(source: str) -> str:
    """读取文本源（文件路径或直接文本）"""
    p = Path(source)
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return source.strip()


def _resolve_roles(roles_path: str | None) -> dict | None:
    """读取角色音色映射 JSON 文件"""
    if not roles_path:
        return None
    import json
    return json.loads(Path(roles_path).read_text(encoding="utf-8"))


def _resolve_bgm(bgm_path: str | None) -> Path | None:
    """解析 BGM 路径"""
    if not bgm_path:
        return None
    p = Path(bgm_path)
    return p if p.exists() else None


def _get_fallback_engine(engine: str) -> str | None:
    """获取引擎的 fallback 对应引擎"""
    if engine == "minimax":
        return "qwen_tts"
    elif engine in ("qwen_tts", "qwen_omni", "qwen"):
        return "minimax"
    return None


def _should_fallback(error_message: str | None, engine: str) -> bool:
    """判断是否应该切换到备用引擎

    以下情况应 fallback：
    - 余额不足（1008）
    - Voice 未授权/不合法（400 + voice）
    - 其他非 retry 类型的 API 错误
    """
    if not error_message:
        return False
    msg = error_message.lower()

    # 余额不足 — MiniMax 特有，重试无效
    if "1008" in msg or "insufficient" in msg or "余额" in msg:
        return True

    # Voice 相关错误 — 换一个引擎可能就解决了
    if ("voice" in msg or "licensed" in msg or "not licensed" in msg) and ("400" in msg or "bad request" in msg or "invalid" in msg):
        return True

    # 其他明确的 API 错误（非网络问题）
    if "api" in msg and ("error" in msg or "失败" in msg or "错误" in msg):
        return True

    return False


def cmd_synthesize(args, container: Container) -> int:
    """synthesize 子命令"""
    text = _resolve_source(args.source)
    if not text:
        logger.error("文本内容为空")
        return 1

    primary_engine = args.engine
    output_path = Path(args.output)

    # 尝试主引擎
    uc = container.synthesize_speech_use_case(primary_engine)
    result = uc.execute(
        text=text,
        output_file=output_path,
        voice_id=args.voice,
        speed=args.speed,
        emotion=args.emotion,
        audio_format=args.format,
    )

    # 失败且可 fallback → 尝试备用引擎
    if not result.success and _should_fallback(result.error_message, primary_engine):
        fallback_engine = _get_fallback_engine(primary_engine)
        if fallback_engine:
            logger.warning(
                f"主引擎 {primary_engine} 失败（{result.error_message}），"
                f"切换到备用引擎 {fallback_engine}..."
            )
            try:
                uc = container.synthesize_speech_use_case(fallback_engine)
                result = uc.execute(
                    text=text,
                    output_file=output_path,
                    voice_id=args.voice,
                    speed=args.speed,
                    emotion=args.emotion,
                    audio_format=args.format,
                )
            except Exception as e:
                logger.error(f"备用引擎 {fallback_engine} 调用异常: {e}")
                return 1

    return 0 if result.success else 1


def cmd_dialogue(args, container: Container) -> int:
    """dialogue 子命令"""
    text = _resolve_source(args.source)
    if not text:
        logger.error("对话脚本为空")
        return 1

    roles = _resolve_roles(args.roles)
    bgm = _resolve_bgm(args.bgm)

    uc = container.dialogue_speech_use_case(args.engine)
    result = uc.execute(
        dialogue_script=text,
        output_file=Path(args.output),
        roles_config=roles,
        bgm_file=bgm,
    )
    return 0 if result.success else 1


def cmd_studio(args, container: Container) -> int:
    """studio 子命令"""
    roles = _resolve_roles(args.roles)
    bgm = _resolve_bgm(args.bgm)

    uc = container.studio_podcast_use_case(llm=args.llm, tts=args.tts)
    result = uc.execute(
        topic=args.topic,
        output_file=Path(args.output),
        roles_config=roles,
        bgm_file=bgm,
    )
    return 0 if result.success else 1


def cmd_batch(args, container: Container) -> int:
    """batch 子命令"""
    # segments 格式: "text1|voice1,text2|voice2,..."
    segments = []
    for item in args.segments.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split("|")
        text = parts[0].strip()
        voice_id = parts[1].strip() if len(parts) > 1 else "male-qn-qingse"
        if not text:
            continue
        segments.append(AudioSegment(text=text, voice_id=voice_id))

    if not segments:
        logger.error("片段列表为空")
        return 1

    uc = container.batch_synthesize_use_case(args.engine)
    result = uc.execute(segments=segments, output_file=Path(args.output))
    return 0 if result.success else 1


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器"""
    parser = argparse.ArgumentParser(
        description="AI Content Studio - 专业级 AI 音频内容创作工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version="ai-studio 1.2.0")
    subparsers = parser.add_subparsers(dest="command", required=False) # Changed required to False to allow --version

    # ── synthesize ────────────────────────────────────────
    p = subparsers.add_parser("synthesize", help="单文本 TTS 合成")
    p.add_argument("--source", required=True, help="文本内容或文件路径")
    p.add_argument("-o", "--output", required=True, help="输出音频文件")
    p.add_argument("--engine", default="minimax",
                   choices=["minimax", "qwen_tts", "qwen_omni", "qwen"])
    p.add_argument("--voice", default="male-qn-qingse", help="音色 ID")
    p.add_argument("--speed", type=float, default=1.0, help="语速 0.5-2.0")
    p.add_argument("--emotion", default="neutral",
                   help="情感 neutral/happy/sad/angry/calm/surprised/fearful/disgusted/fluent")
    p.add_argument("--format", default="mp3", choices=["mp3", "wav"], help="音频格式")
    p.set_defaults(func=cmd_synthesize)

    # ── dialogue ────────────────────────────────────────────
    p = subparsers.add_parser("dialogue", help="对话脚本解析 + 多角色 TTS")
    p.add_argument("--source", required=True, help="对话脚本文件路径")
    p.add_argument("-o", "--output", required=True, help="输出音频文件")
    p.add_argument("--engine", default="minimax",
                   choices=["minimax", "qwen_tts", "qwen_omni", "qwen"])
    p.add_argument("--roles", help="角色音色映射 JSON 文件")
    p.add_argument("--bgm", help="背景音乐文件")
    p.set_defaults(func=cmd_dialogue)

    # ── studio ──────────────────────────────────────────────
    p = subparsers.add_parser("studio", help="LLM 生成 + TTS 全流程播客")
    p.add_argument("--topic", required=True, help="播客主题")
    p.add_argument("-o", "--output", required=True, help="输出音频文件")
    p.add_argument("--llm", default="minimax", choices=["minimax", "qwen"],
                   help="LLM 引擎（生成脚本）")
    p.add_argument("--tts", default="minimax",
                   choices=["minimax", "qwen_tts", "qwen_omni", "qwen"],
                   help="TTS 引擎（语音合成）")
    p.add_argument("--roles", help="角色音色映射 JSON 文件")
    p.add_argument("--bgm", help="背景音乐文件")
    p.set_defaults(func=cmd_studio)

    # ── batch ───────────────────────────────────────────────
    p = subparsers.add_parser("batch", help="批量片段 TTS + 合并")
    p.add_argument("--segments", required=True,
                   help="片段列表，格式: 'text1|voice1,text2|voice2,...'")
    p.add_argument("-o", "--output", required=True, help="输出音频文件")
    p.add_argument("--engine", default="minimax",
                   choices=["minimax", "qwen_tts", "qwen_omni", "qwen"])
    p.set_defaults(func=cmd_batch)

    return parser


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args()

    try:
        container = Container.from_env()
    except Exception as e:
        logger.error(f"容器初始化失败: {e}")
        sys.exit(1)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        exit_code = args.func(args, container)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"错误: {e}")
        sys.exit(1)
    finally:
        container.cleanup()


if __name__ == "__main__":
    main()
