"""
共享音频工具
提供跨模块的音频处理函数
"""
import struct


def make_wav_header(
    num_samples: int,
    sample_rate: int = 24000,
    num_channels: int = 1,
    bits_per_sample: int = 16
) -> bytes:
    """
    为原始 PCM 数据构造标准 WAV header (RIFF fmt + data chunks)

    用于 Qwen Omni 等引擎返回的裸 PCM 数据

    Args:
        num_samples: 样本数（总帧数）
        sample_rate: 采样率（Hz），默认 24000
        num_channels: 声道数，默认 1（单声道）
        bits_per_sample: 位深度，默认 16-bit

    Returns:
        WAV 文件头字节（44 字节）

    Example:
        >>> pcm_data = b'\\x00\\x01\\x02\\x03'  # 原始 PCM 数据
        >>> num_samples = len(pcm_data) // 2  # 16-bit = 2 bytes/sample
        >>> wav_header = make_wav_header(num_samples, sample_rate=24000)
        >>> wav_data = wav_header + pcm_data
        >>> with open("output.wav", "wb") as f:
        ...     f.write(wav_data)

    Note:
        - 符合 RIFF WAVE 格式规范
        - PCM 格式（audio format = 1）
        - Little-endian 字节序
    """
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,      # File size - 8
        b"WAVE",
        b"fmt ",
        16,                  # fmt chunk size (16 for PCM)
        1,                   # Audio format: 1 = PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    return header
