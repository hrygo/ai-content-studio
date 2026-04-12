"""VoiceForge CLI"""
import argparse
import logging
import sys
from pathlib import Path

from voiceforge.infrastructure.container import Container
from voiceforge.use_cases.synthesize import SynthesizeSpeechUseCase

logger = logging.getLogger(__name__)


def _resolve_source(source: str) -> str:
    p = Path(source)
    return p.read_text(encoding="utf-8").strip() if p.exists() else source.strip()


def _resolve_roles(path: str | None) -> dict | None:
    if not path:
        return None
    import json
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve_bgm(path: str | None) -> Path | None:
    if not path:
        return None
    p = Path(path)
    return p if p.exists() else None


def cmd_synthesize(args, container: Container) -> int:
    text = _resolve_source(args.source)
    if not text:
        logger.error("文本内容为空")
        return 1

    engine = args.engine
    uc = container.synthesize_use_case(engine)

    # 主引擎
    result = uc.execute(
        text=text,
        output_file=Path(args.output),
        voice_id=args.voice,
        speed=args.speed,
        emotion=args.emotion,
    )

    # Fallback
    if not result.success:
        fallback = container.get_fallback_tts(engine)
        if fallback:
            logger.warning(f"主引擎 {engine} 失败，切换 fallback")
            uc = SynthesizeSpeechUseCase(engine=fallback)
            result = uc.execute(
                text=text, output_file=Path(args.output),
                voice_id=args.voice, speed=args.speed,
            )

    if result.success:
        logger.info(f"✓ 合成完成: {result.file_path} ({result.duration:.1f}s)")
        return 0
    logger.error(f"✗ 合成失败: {result.error_message}")
    return 1


def cmd_dialogue(args, container: Container) -> int:
    script = _resolve_source(args.source)
    if not script:
        logger.error("对话脚本为空")
        return 1

    uc = container.dialogue_use_case(args.engine)
    result = uc.execute(
        dialogue_script=script,
        output_file=Path(args.output),
        roles_config=_resolve_roles(args.roles),
        bgm_file=_resolve_bgm(args.bgm),
    )

    if result.success:
        logger.info(f"✓ 对话合成完成: {result.file_path} ({result.duration:.1f}s)")
        return 0
    logger.error(f"✗ 对话合成失败: {result.error_message}")
    return 1


def cmd_studio(args, container: Container) -> int:
    uc = container.podcast_use_case(llm=args.llm, tts=args.tts)
    result = uc.execute(
        topic=args.topic,
        output_file=Path(args.output),
        roles_config=_resolve_roles(args.roles),
        bgm_file=_resolve_bgm(args.bgm),
    )

    if result.success:
        logger.info(f"✓ 播客生成完成: {result.file_path} ({result.duration:.1f}s)")
        return 0
    logger.error(f"✗ 播客生成失败: {result.error_message}")
    return 1


def cmd_batch(args, container: Container) -> int:
    from voiceforge.entities import AudioSegment

    segments = []
    for pair in args.segments.split(","):
        parts = pair.strip().rsplit("|", 1)
        if len(parts) == 2:
            segments.append(AudioSegment(text=parts[0].strip(), voice_id=parts[1].strip()))
        else:
            segments.append(AudioSegment(text=parts[0].strip()))

    uc = container.batch_use_case(args.engine)
    result = uc.execute(segments=segments, output_file=Path(args.output))

    if result.success:
        logger.info(f"✓ 批量合成完成: {result.file_path} ({result.duration:.1f}s)")
        return 0
    logger.error(f"✗ 批量合成失败: {result.error_message}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voiceforge",
        description="VoiceForge — 专业级 AI 音频内容创作工具",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    sub = parser.add_subparsers(dest="command", help="子命令")

    # synthesize
    p_syn = sub.add_parser("synthesize", help="单文本 TTS 合成")
    p_syn.add_argument("--source", required=True, help="待合成文本或文件路径")
    p_syn.add_argument("-o", "--output", required=True, help="输出文件路径")
    p_syn.add_argument("--engine", default="minimax", help="TTS 引擎")
    p_syn.add_argument("--voice", default=None, help="音色 ID")
    p_syn.add_argument("--speed", type=float, default=1.0, help="语速")
    p_syn.add_argument("--emotion", default="neutral", help="情感")
    p_syn.add_argument("--format", default="mp3", help="音频格式")

    # dialogue
    p_dia = sub.add_parser("dialogue", help="对话脚本 TTS 合成")
    p_dia.add_argument("--source", required=True, help="对话脚本文件")
    p_dia.add_argument("-o", "--output", required=True, help="输出文件路径")
    p_dia.add_argument("--engine", default="minimax", help="TTS 引擎")
    p_dia.add_argument("--roles", default=None, help="角色音色映射 JSON")
    p_dia.add_argument("--bgm", default=None, help="背景音乐文件")

    # studio
    p_std = sub.add_parser("studio", help="AI 播客工作室")
    p_std.add_argument("--topic", required=True, help="播客主题")
    p_std.add_argument("-o", "--output", required=True, help="输出文件路径")
    p_std.add_argument("--llm", default="minimax", help="LLM 引擎")
    p_std.add_argument("--tts", default="minimax", help="TTS 引擎")
    p_std.add_argument("--roles", default=None, help="角色音色映射 JSON")
    p_std.add_argument("--bgm", default=None, help="背景音乐文件")

    # batch
    p_bat = sub.add_parser("batch", help="批量 TTS 合成")
    p_bat.add_argument("--segments", required=True, help='片段列表 "文本1|音色1,文本2|音色2"')
    p_bat.add_argument("-o", "--output", required=True, help="输出文件路径")
    p_bat.add_argument("--engine", default="minimax", help="TTS 引擎")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not args.command:
        parser.print_help()
        sys.exit(1)

    container = Container.from_env()

    dispatch = {
        "synthesize": cmd_synthesize,
        "dialogue": cmd_dialogue,
        "studio": cmd_studio,
        "batch": cmd_batch,
    }

    handler = dispatch.get(args.command)
    if handler:
        sys.exit(handler(args, container))
    else:
        parser.print_help()
        sys.exit(1)
