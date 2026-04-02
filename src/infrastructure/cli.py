"""
命令行入口
"""
import argparse
import logging
import sys
from pathlib import Path

from ..entities import TTSEngineType, EmotionType, AudioFormat
from ..infrastructure.container import Container


logger = logging.getLogger(__name__)


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description="AI 内容工作室 - TTS 语音合成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 必需参数
    parser.add_argument(
        "--source",
        required=True,
        help="文本源（文件路径或文本内容）",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="输出音频文件路径",
    )

    # 可选参数
    parser.add_argument(
        "--engine",
        choices=[e.value for e in TTSEngineType],
        default=TTSEngineType.MINIMAX.value,
        help=f"TTS 引擎类型（默认: {TTSEngineType.MINIMAX.value}）",
    )

    parser.add_argument(
        "--voice",
        default="male-qn-qingse",
        help="音色 ID（默认: male-qn-qingse）",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="语速 0.5-2.0（默认: 1.0）",
    )

    parser.add_argument(
        "--emotion",
        choices=[e.value for e in EmotionType],
        default=EmotionType.NEUTRAL.value,
        help=f"情感类型（默认: {EmotionType.NEUTRAL.value}）",
    )

    parser.add_argument(
        "--format",
        choices=[f.value for f in AudioFormat],
        default=AudioFormat.MP3.value,
        help=f"音频格式（默认: {AudioFormat.MP3.value}）",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # 1. 初始化容器
        container = Container.from_env()

        # 2. 读取文本
        source_path = Path(args.source)
        if source_path.exists():
            text = source_path.read_text(encoding="utf-8").strip()
        else:
            text = args.source.strip()

        if not text:
            logger.error("文本内容为空")
            sys.exit(1)

        # 3. 执行合成
        output_file = Path(args.output)
        use_case = container.synthesize_speech_use_case(args.engine)

        result = use_case.execute(
            text=text,
            output_file=output_file,
            voice_id=args.voice,
            speed=args.speed,
            emotion=args.emotion,
            audio_format=args.format,
        )

        # 4. 输出结果
        if result.success:
            logger.info(f"✅ 合成成功: {result.file_path}")
            logger.info(f"⏱️  音频时长: {result.duration:.2f} 秒")
            sys.exit(0)
        else:
            logger.error(f"❌ 合成失败: {result.error_message}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(130)

    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        sys.exit(1)

    finally:
        # 清理资源
        if "container" in locals():
            container.cleanup()


if __name__ == "__main__":
    main()
