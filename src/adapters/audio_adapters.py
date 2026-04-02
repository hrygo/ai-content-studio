"""
音频处理器适配器
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional
import subprocess
import logging

from ..entities import EngineResult
from ..use_cases.tts_use_cases import AudioProcessorInterface


logger = logging.getLogger(__name__)


class FFmpegAudioProcessor(AudioProcessorInterface):
    """
    FFmpeg 音频处理器适配器

    职责：
    - 实现 AudioProcessorInterface
    - 调用 FFmpeg 命令
    - 并行处理音频任务
    """

    def __init__(self, max_workers: int = 4):
        """
        初始化 FFmpeg 音频处理器

        Args:
            max_workers: 最大并行工作线程数
        """
        self.max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None

    @property
    def executor(self) -> ThreadPoolExecutor:
        """延迟初始化线程池"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    def merge_audio_files(
        self, audio_files: List[Path], output_file: Path
    ) -> EngineResult:
        """
        合并多个音频文件

        Args:
            audio_files: 音频文件列表
            output_file: 输出文件路径

        Returns:
            EngineResult: 处理结果
        """
        if not audio_files:
            return EngineResult.failure("音频文件列表为空")

        try:
            # 单文件直接复制
            if len(audio_files) == 1:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_bytes(audio_files[0].read_bytes())
                return EngineResult.success(
                    file_path=output_file,
                    duration=self._get_duration(output_file),
                    engine_name="ffmpeg",
                )

            # 多文件合并
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 创建文件列表
            list_file = output_file.parent / "filelist.txt"
            with open(list_file, "w") as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file.absolute()}'\n")

            # FFmpeg 命令
            cmd = [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                "-y",
                str(output_file),
            ]

            # 执行命令
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )

            # 清理临时文件
            list_file.unlink(missing_ok=True)

            # 返回结果
            duration = self._get_duration(output_file)
            return EngineResult.success(
                file_path=output_file, duration=duration, engine_name="ffmpeg"
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 合并失败: {e.stderr}")
            return EngineResult.failure(
                f"FFmpeg 合并失败: {e.stderr}", engine_name="ffmpeg"
            )
        except Exception as e:
            logger.error(f"音频合并异常: {str(e)}")
            return EngineResult.failure(
                f"音频合并异常: {str(e)}", engine_name="ffmpeg"
            )

    def convert_format(
        self, input_file: Path, output_file: Path, format: str = "mp3"
    ) -> EngineResult:
        """
        转换音频格式

        Args:
            input_file: 输入文件
            output_file: 输出文件
            format: 目标格式

        Returns:
            EngineResult: 处理结果
        """
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                "ffmpeg",
                "-i",
                str(input_file),
                "-c:a",
                "libmp3lame" if format == "mp3" else "copy",
                "-y",
                str(output_file),
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            duration = self._get_duration(output_file)
            return EngineResult.success(
                file_path=output_file, duration=duration, engine_name="ffmpeg"
            )

        except Exception as e:
            return EngineResult.failure(
                f"格式转换失败: {str(e)}", engine_name="ffmpeg"
            )

    def adjust_volume(
        self, input_file: Path, output_file: Path, volume: float = 1.0
    ) -> EngineResult:
        """
        调整音量

        Args:
            input_file: 输入文件
            output_file: 输出文件
            volume: 音量倍数

        Returns:
            EngineResult: 处理结果
        """
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            cmd = [
                "ffmpeg",
                "-i",
                str(input_file),
                "-af",
                f"volume={volume}",
                "-y",
                str(output_file),
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            duration = self._get_duration(output_file)
            return EngineResult.success(
                file_path=output_file, duration=duration, engine_name="ffmpeg"
            )

        except Exception as e:
            return EngineResult.failure(
                f"音量调整失败: {str(e)}", engine_name="ffmpeg"
            )

    def _get_duration(self, audio_file: Path) -> float:
        """
        获取音频时长

        Args:
            audio_file: 音频文件

        Returns:
            float: 时长（秒）
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_file),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())

        except Exception:
            # 估算时长（假设 128kbps MP3）
            file_size = audio_file.stat().st_size
            bitrate = 128 * 1024 / 8
            return file_size / bitrate

    def batch_process(self, tasks: List[dict]) -> List[EngineResult]:
        """
        批量并行处理音频任务

        Args:
            tasks: 任务列表，每个任务是一个字典，包含:
                   - method: 方法名（merge, convert, adjust_volume）
                   - args: 参数字典

        Returns:
            List[EngineResult]: 结果列表
        """
        futures = []

        for task in tasks:
            method = task.get("method")
            args = task.get("args", {})

            if method == "merge":
                future = self.executor.submit(
                    self.merge_audio_files, **args
                )
            elif method == "convert":
                future = self.executor.submit(
                    self.convert_format, **args
                )
            elif method == "adjust_volume":
                future = self.executor.submit(
                    self.adjust_volume, **args
                )
            else:
                logger.warning(f"未知方法: {method}")
                continue

            futures.append(future)

        # 等待所有任务完成
        results = [future.result() for future in futures]
        return results

    def cleanup(self):
        """清理资源"""
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None
