"""
音频处理服务
提供音量标准化、混音、音频格式转换等功能
"""
import os
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AudioProcessor:
    """音频处理器"""

    def __init__(self, work_dir: Optional[str] = None):
        """
        初始化音频处理器

        Args:
            work_dir: 临时工作目录
        """
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.gettempdir()) / "audio_processor"
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def normalize_volume(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        target_dbfs: float = -18.0,
        use_compressor: bool = True
    ) -> Optional[str]:
        """
        音量标准化到目标 dBFS

        参考 minimax_aipodcast 的实现，统一音量到 -18 dB

        Args:
            input_file: 输入音频文件
            output_file: 输出文件路径（None 则覆盖原文件）
            target_dbfs: 目标音量（dBFS），默认 -18.0
            use_compressor: 是否使用动态压缩器

        Returns:
            输出文件路径，失败返回 None
        """
        if not os.path.exists(input_file):
            logger.error(f"输入文件不存在: {input_file}")
            return None

        output_path = output_file or input_file
        temp_output = str(self.work_dir / f"normalized_{Path(input_file).name}")

        try:
            # 第一步：分析当前音量
            cmd_analyze = [
                "ffmpeg", "-i", input_file,
                "-af", f"volumedetect",
                "-f", "null", "-"
            ]
            result = subprocess.run(cmd_analyze, capture_output=True, text=True)

            # 提取 mean_volume（简化版本，实际应解析输出）
            # 这里使用更安全的 loudnorm 滤镜

            # 第二步：应用音量标准化
            if use_compressor:
                # 完整处理链：压缩器 → 限制器 → 音量标准化
                filter_complex = (
                    f"acompressor=threshold=-15dB:ratio=4:attack=5:release=50,"
                    f"alimiter=limit=-1.0dB,"
                    f"loudnorm=I={target_dbfs}:TP=-1.5:LRA=11"
                )
            else:
                # 仅音量标准化
                filter_complex = f"loudnorm=I={target_dbfs}:TP=-1.5:LRA=11"

            cmd_normalize = [
                "ffmpeg", "-y", "-i", input_file,
                "-af", filter_complex,
                temp_output
            ]

            subprocess.run(cmd_normalize, capture_output=True, check=True)

            # 移动到最终输出路径
            if output_path != temp_output:
                import shutil
                shutil.move(temp_output, output_path)

            logger.info(f"音量标准化完成: {output_path} (目标: {target_dbfs} dBFS)")
            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg 处理失败: {e}")
            return None
        except Exception as e:
            logger.error(f"音量标准化失败: {e}")
            return None

    def concatenate(
        self,
        audio_files: List[str],
        output_file: str,
        fade_out_duration: int = 1000,
        normalize: bool = True,
        target_dbfs: float = -18.0
    ) -> Optional[str]:
        """
        拼接多个音频文件

        Args:
            audio_files: 音频文件列表
            output_file: 输出文件路径
            fade_out_duration: 最后一个文件的淡出时长（毫秒）
            normalize: 是否标准化音量
            target_dbfs: 目标音量

        Returns:
            输出文件路径，失败返回 None
        """
        if not audio_files:
            logger.error("音频文件列表为空")
            return None

        try:
            # 使用 pydub 进行拼接（更灵活）
            try:
                from pydub import AudioSegment
            except ImportError:
                logger.warning("pydub 未安装，使用 FFmpeg 拼接")
                return self._concatenate_ffmpeg(audio_files, output_file, fade_out_duration)

            # 加载所有音频文件
            combined = AudioSegment.empty()
            for i, audio_file in enumerate(audio_files):
                if not os.path.exists(audio_file):
                    logger.warning(f"文件不存在，跳过: {audio_file}")
                    continue

                audio = AudioSegment.from_file(audio_file)

                # 最后一个文件应用淡出
                if i == len(audio_files) - 1 and fade_out_duration > 0:
                    audio = audio.fade_out(fade_out_duration)

                combined += audio

            # 音量标准化
            if normalize:
                combined = self._normalize_audio_segment(combined, target_dbfs)

            # 导出
            combined.export(output_file, format="mp3")
            logger.info(f"音频拼接完成: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"音频拼接失败: {e}")
            return None

    def _concatenate_ffmpeg(
        self,
        audio_files: List[str],
        output_file: str,
        fade_out_duration: int
    ) -> Optional[str]:
        """使用 FFmpeg 拼接（fallback）"""
        try:
            # 创建文件列表
            list_file = self.work_dir / "concat_list.txt"
            with open(list_file, "w") as f:
                for audio_file in audio_files:
                    f.write(f"file '{audio_file}'\n")

            # FFmpeg 拼接
            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                output_file
            ]

            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"FFmpeg 拼接完成: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"FFmpeg 拼接失败: {e}")
            return None

    def _normalize_audio_segment(self, audio: 'AudioSegment', target_dbfs: float) -> 'AudioSegment':
        """
        标准化 AudioSegment 到目标 dBFS

        参考 minimax_aipodcast 的实现
        """
        from pydub import AudioSegment

        if len(audio) == 0:
            return audio

        # 计算需要的增益
        change_in_dbfs = target_dbfs - audio.dBFS
        return audio.apply_gain(change_in_dbfs)

    def add_bgm(
        self,
        voice_file: str,
        bgm_file: str,
        output_file: str,
        bgm_volume: float = 0.15,
        normalize: bool = True,
        target_dbfs: float = -18.0
    ) -> Optional[str]:
        """
        添加背景音乐

        Args:
            voice_file: 人声文件
            bgm_file: 背景音乐文件
            output_file: 输出文件
            bgm_volume: BGM 音量（0.0-1.0）
            normalize: 是否标准化音量
            target_dbfs: 目标音量

        Returns:
            输出文件路径，失败返回 None
        """
        if not os.path.exists(voice_file) or not os.path.exists(bgm_file):
            logger.error("输入文件不存在")
            return None

        try:
            # 使用现有的混音引擎（audio_utils.merge_audio_files）
            # 这里提供简化版本
            cmd = [
                "ffmpeg", "-y",
                "-i", voice_file,
                "-i", bgm_file,
                "-filter_complex",
                f"[1:a]volume={bgm_volume}[bgm];"
                f"[0:a][bgm]amix=inputs=2:duration=longest",
                "-ac", "2",
                output_file
            ]

            subprocess.run(cmd, capture_output=True, check=True)

            # 后处理：音量标准化
            if normalize:
                self.normalize_volume(output_file, output_file, target_dbfs)

            logger.info(f"BGM 混音完成: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"BGM 混音失败: {e}")
            return None

    def get_duration(self, file_path: str) -> float:
        """获取音频时长（秒）"""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            return float(output)
        except Exception:
            return 0.0


# 便捷函数
def normalize_volume(input_file: str, output_file: Optional[str] = None, target_dbfs: float = -18.0) -> Optional[str]:
    """便捷函数：音量标准化"""
    processor = AudioProcessor()
    return processor.normalize_volume(input_file, output_file, target_dbfs)


def concatenate(audio_files: List[str], output_file: str, normalize: bool = True) -> Optional[str]:
    """便捷函数：音频拼接"""
    processor = AudioProcessor()
    return processor.concatenate(audio_files, output_file, normalize=normalize)
