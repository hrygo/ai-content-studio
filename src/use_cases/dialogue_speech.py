"""
对话播报用例 - 对话脚本解析 + TTS 合成

职责：
- 解析对话脚本（[角色名]: 发言内容 格式）
- 批量 TTS 合成
- 音频合并与混音
"""
import re
import logging
from pathlib import Path
from typing import List, Optional, Dict

from ..entities import AudioSegment, EngineResult
from .tts_use_cases import TTSEngineInterface, BatchSynthesizeUseCase
from ..adapters.audio_adapters import FFmpegAudioProcessor

logger = logging.getLogger(__name__)

# 默认角色音色映射
DEFAULT_ROLES_CONFIG: Dict[str, str] = {
    "Alex": "male-qn-qingse",
    "Sam": "male-qn-jingpin",
    "Kim": "female-tianmei",
}


def parse_dialogue_segments(
    script_text: str,
    roles_config: Optional[Dict[str, str]] = None,
) -> List[AudioSegment]:
    """
    解析对话脚本，返回 AudioSegment 列表

    支持格式：
        [角色名]: 发言内容
        [Alex]: 大家好，今天我们来聊聊...

    Args:
        script_text: 对话脚本文本
        roles_config: 角色音色映射，如 {"Alex": "male-qn-qingse"}

    Returns:
        AudioSegment 列表，解析失败返回空列表
    """
    config = roles_config or DEFAULT_ROLES_CONFIG

    # 匹配 [角色名]: 发言内容
    pattern = re.compile(r"^\[([^\]]+)\]:\s*(.+)$", re.MULTILINE)
    matches = pattern.findall(script_text)

    if not matches:
        return []

    segments: List[AudioSegment] = []
    for speaker, text in matches:
        speaker = speaker.strip()
        text = text.strip()

        if not text:
            continue

        # 查找音色 ID（优先使用 roles_config，否则使用默认映射）
        voice_id = config.get(speaker)
        if voice_id is None:
            # 尝试默认映射
            voice_id = DEFAULT_ROLES_CONFIG.get(speaker, "male-qn-qingse")
            logger.warning(
                f"角色 '{speaker}' 未在 roles_config 中指定，使用默认音色: {voice_id}"
            )

        try:
            segment = AudioSegment(text=text, voice_id=voice_id)
            segments.append(segment)
        except ValueError as e:
            logger.warning(f"跳过无效片段 [{speaker}]: {e}")
            continue

    return segments


class DialogueSpeechUseCase:
    """
    对话播报用例

    全流程：解析对话脚本 → 批量 TTS → 音频合并

    Example:
        >>> use_case = DialogueSpeechUseCase(
        ...     engine=minimax_engine,
        ...     audio_processor=FFmpegAudioProcessor(),
        ... )
        >>> result = use_case.execute(
        ...     dialogue_script="[Alex]: 你好\\n[Sam]: 你好！",
        ...     output_file=Path("output.mp3"),
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        engine: TTSEngineInterface,
        audio_processor: FFmpegAudioProcessor,
    ):
        """
        初始化对话播报用例

        Args:
            engine: TTS 引擎
            audio_processor: FFmpeg 音频处理器
        """
        self.engine = engine
        self.audio_processor = audio_processor
        self._batch_uc: Optional[BatchSynthesizeUseCase] = None

    @property
    def batch_uc(self) -> BatchSynthesizeUseCase:
        """延迟创建 BatchSynthesizeUseCase"""
        if self._batch_uc is None:
            self._batch_uc = BatchSynthesizeUseCase(
                engine=self.engine,
                audio_processor=self.audio_processor,
            )
        return self._batch_uc

    def execute(
        self,
        dialogue_script: str,
        output_file: Path,
        roles_config: Optional[Dict[str, str]] = None,
        bgm_file: Optional[Path] = None,
        sample_rate: int = 32000,
    ) -> EngineResult:
        """
        执行对话 TTS 全流程

        Args:
            dialogue_script: 对话脚本（如 "[Alex]: 你好" 格式）
            output_file: 输出音频文件
            roles_config: 角色音色映射
            bgm_file: 背景音乐文件（可选）
            sample_rate: 采样率（仅影响 BGM 混音）

        Returns:
            EngineResult: 生成结果
        """
        # 1. 解析对话
        segments = parse_dialogue_segments(dialogue_script, roles_config)
        if not segments:
            return EngineResult.failure("对话脚本解析失败，无有效片段")

        logger.info(f"解析到 {len(segments)} 个对话片段")

        # 2. 批量 TTS 合成
        merge_result = self.batch_uc.execute(
            segments=segments,
            output_file=output_file,
            merge=True,
        )

        if not merge_result.success:
            return merge_result

        # 3. 混音（如果提供了 BGM）
        if bgm_file and bgm_file.exists():
            logger.info(f"正在混音 BGM: {bgm_file}")
            return self._mix_with_bgm(output_file, bgm_file, sample_rate)

        return merge_result

    def _mix_with_bgm(
        self,
        voice_file: Path,
        bgm_file: Path,
        sample_rate: int,
    ) -> EngineResult:
        """
        将语音与背景音乐混音

        Args:
            voice_file: 语音文件
            bgm_file: BGM 文件
            sample_rate: 采样率

        Returns:
            EngineResult: 混音结果
        """
        import subprocess

        output_file = voice_file.with_suffix(".mixed.mp3")
        voice_file.rename(output_file)  # 临时移动

        try:
            cmd = [
                "ffmpeg",
                "-i", str(output_file),
                "-i", str(bgm_file),
                "-filter_complex",
                "[0:a]volume=1.0[voice];[1:a]volume=0.3[bgm];[voice][bgm]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:a", "libmp3lame",
                "-q:a", "2",
                "-y",
                str(voice_file),
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
            output_file.unlink(missing_ok=True)

            duration = self.audio_processor._get_duration(voice_file)
            return EngineResult.success(
                file_path=voice_file,
                duration=duration,
                engine_name="ffmpeg",
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"BGM 混音失败: {e.stderr}")
            # 恢复语音文件
            output_file.rename(voice_file)
            return EngineResult.failure(f"BGM 混音失败: {e.stderr}")
        except Exception as e:
            logger.error(f"混音异常: {e}")
            try:
                output_file.rename(voice_file)
            except Exception:
                pass
            return EngineResult.failure(f"混音异常: {e}")
