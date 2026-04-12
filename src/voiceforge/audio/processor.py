"""FFmpeg 音频处理器"""
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from voiceforge.entities import EngineResult

logger = logging.getLogger(__name__)


class FFmpegAudioProcessor:
    """FFmpeg 音频处理器（合并、混音、格式转换）"""

    def __init__(self, max_workers: int = 4):
        self._executor: ThreadPoolExecutor | None = None
        self.max_workers = max_workers

    @property
    def executor(self) -> ThreadPoolExecutor:
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    def merge_audio_files(
        self,
        audio_files: list[Path],
        output_file: Path,
        pan_list: list[float] | None = None,
        bgm_file: Path | None = None,
        sample_rate: int = 32000,
    ) -> EngineResult:
        """合并多个音频文件（支持立体声定位和 BGM 混音）"""
        if not audio_files:
            return EngineResult.fail("音频文件列表为空")

        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            has_pan = pan_list and len(pan_list) == len(audio_files)
            has_bgm = bgm_file is not None and bgm_file.exists()

            # 单文件无特效：直接复制
            if len(audio_files) == 1 and not has_pan and not has_bgm:
                output_file.write_bytes(audio_files[0].read_bytes())
                return EngineResult.ok(output_file, self._estimate_duration(output_file), "ffmpeg")

            # 构建 filter_complex
            filter_parts: list[str] = []
            concat_inputs = ""

            for i, audio_file in enumerate(audio_files):
                pan_val = pan_list[i] if has_pan else 0.0
                gain_l = max(0.0, (1.0 - pan_val) / 2)
                gain_r = max(0.0, (1.0 + pan_val) / 2)
                filter_parts.append(
                    f"[{i}:a]pan=stereo|c0={gain_l:.3f}*c0|c1={gain_r:.3f}*c0[a{i}]"
                )
                concat_inputs += f"[a{i}]"

            if len(audio_files) > 1:
                filter_parts.append(f"{concat_inputs}concat=n={len(audio_files)}:v=0:a=1[out]")

            if has_bgm:
                if len(audio_files) > 1:
                    filter_parts[-1] = (
                        f"{concat_inputs}concat=n={len(audio_files)}:v=0:a=1[pre];"
                        f"[pre]volume=1.0[pre];"
                        f"[{len(audio_files)}:a]volume=0.4[bgm];"
                        f"[pre][bgm]amix=inputs=2:duration=first[out]"
                    )
                else:
                    filter_parts.append(
                        f"[0:a]volume=1.0[pre];"
                        f"[{len(audio_files)}:a]volume=0.4[bgm];"
                        f"[pre][bgm]amix=inputs=2:duration=first[out]"
                    )

            filter_complex = ";".join(filter_parts)
            all_inputs = [str(f) for f in audio_files]
            if has_bgm:
                all_inputs.append(str(bgm_file))

            cmd = [
                "ffmpeg", "-y",
                *sum([["-i", p] for p in all_inputs], []),
                "-filter_complex", filter_complex,
                "-map", "[out]", "-ar", str(sample_rate),
                "-ac", "2", "-q:a", "2",
                str(output_file),
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
            return EngineResult.ok(output_file, self._estimate_duration(output_file), "ffmpeg")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 合并失败: {e.stderr}")
            return EngineResult.fail(f"FFmpeg 合并失败: {e.stderr}", "ffmpeg")
        except Exception as e:
            logger.error(f"音频合并异常: {e}")
            return EngineResult.fail(str(e), "ffmpeg")

    def _estimate_duration(self, audio_file: Path) -> float:
        """估算音频时长"""
        file_size = audio_file.stat().st_size
        if audio_file.suffix.lower() == ".wav":
            return max(0, (file_size - 44)) / (24000 * 2)
        return file_size / (128 * 1024 / 8)

    def cleanup(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
