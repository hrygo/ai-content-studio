"""
对话脚本解析 + 多角色 TTS 用例

职责：
- 解析对话脚本格式 [Speaker]: text 或 [Speaker, emotion]: text
- 为各角色分配音色
- 调用 TTS 引擎合成各段
- FFmpeg 混音（立体声 + 可选 BGM）
- 支持 fallback 机制
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import re as _re
import logging
from itertools import cycle

from ..entities import AudioSegment, EngineResult, TTSRequest, VoiceConfig
from .tts_use_cases import TTSEngineInterface
from ..adapters.audio_adapters import FFmpegAudioProcessor
from ..entities.errors import ErrorType

logger = logging.getLogger(__name__)

# 对话解析正则
_SEGMENT_PATTERN = _re.compile(
    r"\[([^\],]+?)(?:,\s*([^\]]+?))?\]:\s*((?:.|\n)*?)(?=\[([^\],]+?)(?:,\s*([^\]]+?))?\]:|$)",
    _re.DOTALL,
)


def parse_dialogue_segments(text: str) -> List[Tuple[AudioSegment, str]]:
    """
    解析对话脚本文本，返回 (AudioSegment, emotion) 元组列表

    支持格式：
      [Speaker]: text content
      [Speaker, emotion]: text content

    支持同行多角色：[Alex]: 你好[Sam]: 你好

    Args:
        text: 对话脚本文本

    Returns:
        List[Tuple[AudioSegment, str]]: (音频片段, 情感) 元组列表
    """
    result: List[Tuple[AudioSegment, str]] = []
    for match in _SEGMENT_PATTERN.finditer(text):
        speaker = match.group(1).strip()
        emotion = match.group(2).strip() if match.group(2) else "neutral"
        content = match.group(3).strip()
        if not content:
            continue
        segment = AudioSegment(text=content, voice_id=speaker)
        result.append((segment, emotion))
    return result


class VoiceAllocator:
    """音色分配器 - 将 speaker name 映射到 voice_id"""

    DEFAULT_VOICES = ["cherry", "ethan", "chelsie"]

    def __init__(self, roles_config: Optional[Dict] = None):
        self._roles = roles_config or {}
        # 预构建小写键映射，O(1) 查找
        self._lower_roles: Dict[str, Tuple[str, dict]] = {
            k.lower(): (k, v) for k, v in self._roles.items()
        }
        self._pool: cycle = cycle(self.DEFAULT_VOICES)
        self._assigned: Dict[str, str] = {}

    def get_voice(self, speaker: str) -> str:
        """获取 speaker 对应的 voice_id"""
        # 优先使用 roles_config 中的显式映射（O(1) 小写键查找）
        key = speaker.lower()
        if key in self._lower_roles:
            _, role_cfg = self._lower_roles[key]
            if isinstance(role_cfg, dict):
                return role_cfg.get("voice", self.DEFAULT_VOICES[0])
            return str(role_cfg)
        # 其次使用已分配的角色
        if speaker in self._assigned:
            return self._assigned[speaker]
        # 轮询分配（cycle 永不耗尽）
        voice = next(self._pool)
        self._assigned[speaker] = voice
        return voice


def compute_role_pan_values(unique_roles: List[str]) -> Dict[str, float]:
    """
    计算每个角色的立体声声道值（用于 FFmpeg pan filter）

    公式：pan = -0.8 + 1.6 * i / (n-1)
    - 单角色：0.0（居中）
    - 双角色：-0.8（左）、0.8（右）
    - 多角色：均匀分布在 [-0.8, 0.8] 区间
    """
    if len(unique_roles) <= 1:
        return {role: 0.0 for role in unique_roles}
    return {
        role: round(-0.8 + (1.6 * i / (len(unique_roles) - 1)), 2)
        for i, role in enumerate(unique_roles)
    }


def _get_engine_name(engine: TTSEngineInterface) -> str:
    """获取引擎名称"""
    return getattr(engine, "get_engine_name", lambda: "unknown")()


@dataclass
class DialogueSpeechUseCase:
    """
    对话脚本 TTS 用例

    职责：
    - 解析对话脚本
    - 音色分配
    - 批量 TTS 合成（支持 fallback）
    - FFmpeg 混音（立体声 + BGM）
    """

    engine: TTSEngineInterface
    audio_processor: FFmpegAudioProcessor
    fallback_engine: Optional[TTSEngineInterface] = None  # 备用引擎（可选）

    def execute(
        self,
        dialogue_script: str,
        output_file: Path,
        roles_config: Optional[Dict] = None,
        bgm_file: Optional[Path] = None,
        sample_rate: int = 32000,
    ) -> EngineResult:
        """
        执行对话脚本 TTS 合成

        Args:
            dialogue_script: 对话脚本文本
            output_file: 输出音频文件路径
            roles_config: 角色音色映射 {"Alex": {"voice": "cherry", ...}, ...}
            bgm_file: 背景音乐文件路径
            sample_rate: 采样率

        Returns:
            EngineResult: 合成结果
        """
        # 1. 解析对话
        segments = parse_dialogue_segments(dialogue_script)
        if not segments:
            return EngineResult.failure("对话脚本为空或无法解析")

        # 2. 分配音色
        allocator = VoiceAllocator(roles_config)
        unique_roles: List[str] = []
        segments_with_voices: List[Tuple[AudioSegment, str, str]] = []
        for segment, emotion in segments:
            voice_id = allocator.get_voice(segment.voice_id)
            if segment.voice_id not in unique_roles:
                unique_roles.append(segment.voice_id)
            segments_with_voices.append((segment, emotion, voice_id))

        # 3. 计算声道值
        pan_values = compute_role_pan_values(unique_roles)

        # 4. 逐段 TTS 合成（支持 fallback）
        audio_files: List[Path] = []
        for i, (segment, emotion, voice_id) in enumerate(segments_with_voices, 1):
            temp_file = output_file.parent / f"_temp_{len(audio_files)}_{output_file.stem}.mp3"
            request = TTSRequest(
                text=segment.text,
                output_file=temp_file,
                voice_config=VoiceConfig(
                    voice_id=voice_id,
                    speed=1.0,
                    volume=1.0,
                    pitch=0,
                    emotion=emotion or "neutral",
                ),
            )

            # 主引擎合成
            result = self.engine.synthesize(request)

            # 失败时尝试 fallback
            if not result.success and self._should_fallback(result.error_message):
                result = self._try_fallback(request, i)

            # 仍然失败，返回错误
            if not result.success:
                # 清理已生成的临时文件
                for f in audio_files:
                    f.unlink(missing_ok=True)
                return EngineResult.failure(
                    f"片段 {i} TTS 合成失败（已尝试 fallback）: {result.error_message}"
                )

            audio_files.append(result.file_path)

        # 5. FFmpeg 混音
        if len(audio_files) == 1 and not bgm_file:
            # 单段无 BGM：直接重命名，使用真实时长
            audio_files[0].rename(output_file)
            duration = self.audio_processor._get_duration(output_file)
            return EngineResult.success(
                file_path=output_file,
                duration=duration,
                engine_name=_get_engine_name(self.engine),
            )

        # 多段混音或有 BGM
        pan_list = [pan_values.get(seg.voice_id, 0.0) for seg, _, _ in segments_with_voices]
        merge_result = self.audio_processor.merge_audio_files(
            audio_files=audio_files,
            output_file=output_file,
            pan_list=pan_list,
            bgm_file=bgm_file,
            sample_rate=sample_rate,
        )

        # 6. 清理临时文件
        for f in audio_files:
            f.unlink(missing_ok=True)

        return merge_result

    def _should_fallback(self, error_message: str | None) -> bool:
        """判断是否应该切换到备用引擎"""
        if not self.fallback_engine:
            return False

        error_type = ErrorType.classify(error_message)
        return error_type == ErrorType.FALLBACK

    def _try_fallback(
        self, request: TTSRequest, segment_index: int
    ) -> EngineResult:
        """尝试使用 fallback 引擎合成"""
        if not self.fallback_engine:
            return EngineResult.failure("没有配置 fallback 引擎")

        engine_name = _get_engine_name(self.fallback_engine)
        logger.warning(
            f"片段 {segment_index} 主引擎失败，切换到 fallback 引擎: {engine_name}"
        )

        try:
            result = self.fallback_engine.synthesize(request)
            return result
        except Exception as e:
            logger.error(f"Fallback 引擎调用异常: {e}")
            return EngineResult.failure(f"Fallback 引擎失败: {str(e)}")
