"""音频工具函数"""
import struct
import subprocess
from pathlib import Path


def wav_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "128k") -> None:
    """WAV 转 MP3（ffmpeg）"""
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-b:a", bitrate, str(mp3_path)],
        capture_output=True, check=True,
    )


def save_audio(audio_data: bytes, output_file: Path, *, is_wav: bool = True) -> None:
    """保存音频数据，按后缀自动转换格式

    WAV-only 引擎输出的数据直接写入 .wav；
    若目标后缀是 .mp3 则先写 wav 再 ffmpeg 转。
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not is_wav or output_file.suffix.lower() == ".wav":
        output_file.write_bytes(audio_data)
        return

    # 需要转 MP3
    wav_path = output_file.with_suffix(".wav")
    wav_path.write_bytes(audio_data)
    wav_to_mp3(wav_path, output_file)
    wav_path.unlink(missing_ok=True)


def make_wav_header(pcm: bytes, sample_rate: int = 24000, channels: int = 1, bits: int = 16) -> bytes:
    """给裸 PCM 数据添加 WAV 文件头"""
    data_size = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, channels, sample_rate,
        sample_rate * channels * bits // 8,
        channels * bits // 8, bits,
        b"data", data_size,
    )
    return header + pcm


def estimate_duration(file_path: Path, default_bitrate_kbps: int = 128) -> float:
    """估算音频时长"""
    file_size = file_path.stat().st_size
    if file_path.suffix.lower() == ".wav":
        return max(0, file_size - 44) / (24000 * 2)
    return file_size / (default_bitrate_kbps * 1024 / 8)
