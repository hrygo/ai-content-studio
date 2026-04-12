"""对话脚本 TTS 用例"""
import re
import logging
from dataclasses import dataclass
from itertools import cycle
from pathlib import Path

from voiceforge.entities import AudioSegment, EngineResult, TTSRequest, VoiceConfig
from voiceforge.protocols.engine import TTSEngine
from voiceforge.protocols.processor import AudioProcessor
from .synthesize import _should_fallback, _try_fallback_synthesize

logger = logging.getLogger(__name__)

# 对话解析正则
_SEGMENT_RE = re.compile(
    r"\[([^\],]+?)(?:,\s*([^\]]+?))?\]:\s*((?:.|\n)*?)(?=\[([^\],]+?)(?:,\s*([^\]]+?))?\]:|$)",
    re.DOTALL,
)


def parse_dialogue_segments(text: str) -> list[tuple[AudioSegment, str]]:
    """解析对话脚本 → [(AudioSegment, emotion)]"""
    result: list[tuple[AudioSegment, str]] = []
    for m in _SEGMENT_RE.finditer(text):
        speaker = m.group(1).strip()
        emotion = m.group(2).strip() if m.group(2) else "neutral"
        content = m.group(3).strip()
        if content:
            result.append((AudioSegment(text=content, voice_id=speaker), emotion))
    return result


class VoiceAllocator:
    """将 speaker name 映射到 voice_id"""
    DEFAULT_VOICES = ["cherry", "ethan", "chelsie"]

    def __init__(self, roles_config: dict | None = None):
        self._roles = {k.lower(): v for k, v in (roles_config or {}).items()}
        self._pool = cycle(self.DEFAULT_VOICES)
        self._assigned: dict[str, str] = {}

    def get_voice(self, speaker: str) -> str:
        key = speaker.lower()
        if key in self._roles:
            cfg = self._roles[key]
            return cfg.get("voice", self.DEFAULT_VOICES[0]) if isinstance(cfg, dict) else str(cfg)
        if speaker in self._assigned:
            return self._assigned[speaker]
        voice = next(self._pool)
        self._assigned[speaker] = voice
        return voice


def compute_pan_values(unique_roles: list[str]) -> dict[str, float]:
    """计算立体声声道值"""
    if len(unique_roles) <= 1:
        return {r: 0.0 for r in unique_roles}
    return {
        r: round(-0.8 + 1.6 * i / (len(unique_roles) - 1), 2)
        for i, r in enumerate(unique_roles)
    }


@dataclass
class DialogueSpeechUseCase:
    """对话脚本 TTS（含 fallback）"""

    engine: TTSEngine
    audio_processor: AudioProcessor
    fallback_engine: TTSEngine | None = None

    def execute(
        self,
        dialogue_script: str,
        output_file: Path,
        roles_config: dict | None = None,
        bgm_file: Path | None = None,
        sample_rate: int = 32000,
    ) -> EngineResult:
        segments = parse_dialogue_segments(dialogue_script)
        if not segments:
            return EngineResult.fail("对话脚本为空或无法解析")

        allocator = VoiceAllocator(roles_config)
        unique_roles: list[str] = []
        prepared: list[tuple[AudioSegment, str, str]] = []

        for seg, emotion in segments:
            voice_id = allocator.get_voice(seg.voice_id)
            if seg.voice_id not in unique_roles:
                unique_roles.append(seg.voice_id)
            prepared.append((seg, emotion, voice_id))

        pan_values = compute_pan_values(unique_roles)

        # 逐段合成
        audio_files: list[Path] = []
        for i, (seg, emotion, voice_id) in enumerate(prepared, 1):
            temp_file = output_file.parent / f"_temp_{len(audio_files)}_{output_file.stem}.mp3"
            request = TTSRequest(
                text=seg.text, output_file=temp_file,
                voice_config=VoiceConfig(voice_id=voice_id, emotion=emotion),
            )

            result = self.engine.synthesize(request)
            if not result.success and _should_fallback(self.fallback_engine, result.error_message):
                result = _try_fallback_synthesize(self.fallback_engine, request, i)
            if not result.success:
                for f in audio_files:
                    f.unlink(missing_ok=True)
                return EngineResult.fail(f"片段 {i} 合成失败: {result.error_message}")

            if result.file_path:
                audio_files.append(result.file_path)

        # 混音
        if len(audio_files) == 1 and not bgm_file:
            audio_files[0].rename(output_file)
            return EngineResult.ok(output_file, 0.0, self.engine.get_engine_name())

        pan_list = [pan_values.get(seg.voice_id, 0.0) for seg, _, _ in prepared]
        merge_result = self.audio_processor.merge_audio_files(
            audio_files, output_file, pan_list=pan_list,
            bgm_file=bgm_file, sample_rate=sample_rate,
        )

        for f in audio_files:
            f.unlink(missing_ok=True)

        return merge_result
