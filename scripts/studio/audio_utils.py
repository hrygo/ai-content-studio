"""
audio_utils.py - AI Content Studio 共享音频工具
FFmpeg 辅助 + 文本切分 + 混音引擎，两个 TTS 引擎通用
"""
import os
import subprocess
import re as _re
import json as _json
import struct as _struct
from pathlib import Path


def get_duration(file_path):
    """获取音频文件时长 (秒)"""
    abs_path = str(Path(file_path).resolve())
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        abs_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(output)
    except Exception:
        return 0.0


def run_ffmpeg(cmd_list, log_file):
    """安全执行 FFmpeg 命令"""
    try:
        with open(log_file, "w") as f:
            result = subprocess.run(
                cmd_list,
                stdout=f,
                stderr=subprocess.STDOUT,
                check=True
            )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False


def split_text(text, max_len=300):
    """
    按标点符号智能切分长文本
    两个 TTS 引擎通用，逻辑完全一致
    """
    if len(text) <= max_len:
        return [text]
    delimiters = ["\u3002", "\uff01", "\uff1f", "\uff1b", ".", "!", "?", ";", "\n"]
    chunks = []
    current_chunk = ""
    for char in text:
        current_chunk += char
        if char in delimiters and len(current_chunk) >= max_len * 0.6:
            chunks.append(current_chunk.strip())
            current_chunk = ""
    if current_chunk:
        chunks.append(current_chunk.strip())
    final_chunks = []
    for c in chunks:
        if len(c) > max_len:
            for i in range(0, len(c), max_len):
                final_chunks.append(c[i:i + max_len])
        else:
            final_chunks.append(c)
    return final_chunks


# ── 对话脚本正则解析 ────────────────────────────────────────

_SEGMENT_PATTERN = _re.compile(r"\[([^\],]+)(?:,\s*([^\]]+))?\]:\s*(.*)")


def parse_dialogue_segments(file_path):
    """
    从对话 TXT 文件解析 segments 列表
    文件格式：[角色, 情感]: 文本内容

    返回: list[dict]  {"role": str, "emotion": str, "text": str}
    """
    segments = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            script_text = f.read()
    except Exception:
        return []
    return parse_dialogue_segments_from_text(script_text)


def parse_dialogue_segments_from_text(script_text):
    """
    从对话文本字符串解析 segments 列表
    支持格式：
      [Speaker]: content
      [Speaker, emotion]: content

    返回: list[dict]  {"role": str, "emotion": str, "text": str}
    """
    segments = []
    for line in script_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = _SEGMENT_PATTERN.match(line)
        if match:
            segments.append({
                "role": match.group(1).strip(),
                "emotion": match.group(2).strip() if match.group(2) else "neutral",
                "text": match.group(3).strip()
            })
        elif line:
            segments.append({"role": "Narrator", "emotion": "neutral", "text": line})
    return segments


# 别名：兼容两个 TTS 工具的导入名
parse_dialogue_text = parse_dialogue_segments


# ── 音色池 ────────────────────────────────────────────────────

class VoicePool:
    """
    音色分配器：自动为未配置角色分配音色（轮询策略）
    支持优先级：显式分配 > 预分配 > 轮询
    """
    def __init__(self, voices=None):
        self._voices = voices or ["cherry", "ethan", "chelsie"]
        self._assigned = {}   # role_label -> voice
        self._idx = 0
        self._warned = False

    @property
    def default_voice(self):
        return self._voices[0]

    def assign(self, role_label, voice):
        """为角色分配指定音色"""
        self._assigned[role_label] = voice

    def get(self, role_label):
        """获取角色的音色，未分配则自动轮询分配"""
        if role_label in self._assigned:
            return self._assigned[role_label]
        voice = self._voices[self._idx % len(self._voices)]
        self._idx += 1
        if self._idx == 1:
            self._warned = True
        return voice

    @property
    def exhausted(self):
        return self._warned


# ── 立体声声道分配 ─────────────────────────────────────────

def compute_role_pan_values(unique_roles):
    """
    等间距分配立体声声道值（从左到右均匀分布）
    单角色 → 居中 (0)，多角色 → [-0.8, +0.8] 区间等距
    """
    if len(unique_roles) <= 1:
        return {role: 0 for role in unique_roles}
    return {
        role: -0.8 + (1.6 * i / (len(unique_roles) - 1))
        for i, role in enumerate(unique_roles)
    }


# ── SSE / WAV 工具 ──────────────────────────────────────────

def stream_qwen_omni_events(resp):
    """
    SSE 事件解析器：解析 Qwen Omni / Chat Completions 流式响应
    yields: delta dict from each SSE data chunk
    """
    for line in resp.iter_lines():
        if not line:
            continue
        if line.startswith(b":") or line.strip() in (b"data: [DONE]", b""):
            continue
        if not line.startswith(b"data: "):
            continue
        data_str = line.decode("utf-8")[6:].strip()
        if not data_str or data_str == "[DONE]":
            continue
        try:
            chunk = _json.loads(data_str)
        except _json.JSONDecodeError:
            continue
        choices = chunk.get("choices")
        if not choices:
            continue
        yield choices[0].get("delta", {})


def make_wav_header(num_samples, sample_rate=24000, num_channels=1, bits_per_sample=16):
    """
    为原始 PCM 数据构造标准 WAV header (RIFF fmt + data chunks)
    用于 qwen3-omni-flash 返回的裸 PCM 数据
    """
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    header = _struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,           # fmt chunk size
        1,             # audio format: PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header


# ── 共享混音引擎 ────────────────────────────────────────────
# 统一 aformat 采样率 + adelay 时序编排 + amix=duration=longest
# 调用方通过 sample_rate / output_suffix / work_dir_name 控制差异


def merge_audio_files(file_list, output_file, pan_list=None, bgm_file=None,
                     sample_rate=32000, work_dir_name="work", output_suffix=".mp3"):
    """
    FFmpeg 混音引擎：顺序拼接多片段（支持立体声 / BGM 混音）
    两引擎共用，差异通过参数注入。

    Args:
        file_list: 音频片段路径列表
        output_file: 输出文件路径
        pan_list: 声道平衡列表
        bgm_file: 背景音乐文件路径
        sample_rate: 采样率 (minimax=32000, qwen=24000)
        work_dir_name: 工作目录名 (默认为 "work"，三引擎整合)
        output_suffix: 输出格式后缀 (.mp3 或 .wav)
    """
    if not file_list:
        return False

    from paths import WORK_DIR, WORK_QWEN_DIR, WORK_TTS_DIR
    # 根据工作目录名选择对应路径
    work_dir_map = {
        "work": WORK_DIR,
        "work_qwen": WORK_QWEN_DIR,
        "work_tts": WORK_TTS_DIR,
    }
    work_dir = work_dir_map.get(work_dir_name, WORK_DIR)

    # 计算每段时长
    segment_durations_ms = [int(get_duration(f) * 1000) for f in file_list]

    # 立体声处理
    processed_list = []
    for i, (f, balance) in enumerate(zip(file_list, pan_list or [0] * len(file_list))):
        if balance == 0:
            processed_list.append(f)
        else:
            l_vol = 1.0 if balance <= 0 else max(0.1, 1.0 - balance)
            r_vol = 1.0 if balance >= 0 else max(0.1, 1.0 + balance)
            panned_temp = work_dir / f"panned_{i}.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", f,
                 "-af", f"pan=stereo|c0={l_vol:.1f}*c0|c1={r_vol:.1f}*c0",
                 str(panned_temp)],
                capture_output=True,
            )
            processed_list.append(str(panned_temp))

    # 构建 filter_complex
    inputs = []
    filter_parts = []
    current_time_ms = 0

    for i, f in enumerate(processed_list):
        inputs.extend(["-i", f])
        dur = segment_durations_ms[i]
        overlap_ms = 150 if i > 0 else 0
        delay = max(0, current_time_ms - overlap_ms)
        filter_parts.append(
            f"[{i}:a]aformat=sample_fmts=s16:sample_rates={sample_rate}:channel_layouts=mono,"
            f"adelay={delay}|{delay}[a{i}];"
        )
        current_time_ms += dur

    n = len(processed_list)
    amix_inputs = "".join([f"[a{i}]" for i in range(n)])
    master_v = (
        f"{amix_inputs}amix=inputs={n}:duration=longest,"
        f"acompressor=threshold=-15dB:ratio=4:attack=5:release=50,"
        f"alimiter=limit=-1.0dB,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11"
    )
    filter_parts.append(f"{master_v}[mixed_voice];")

    if bgm_file and os.path.exists(bgm_file):
        inputs.extend(["-i", bgm_file])
        bgm_idx = n
        filter_parts.append(
            f"[{bgm_idx}:a]volume=0.15,acompressor=threshold=-40dB:ratio=20:attack=5:release=200[bgm_ducked];"
            f"[mixed_voice][bgm_ducked]amix=inputs=2:duration=longest[out]"
        )
    else:
        filter_parts.append("[mixed_voice]volume=1.0[out]")

    filter_complex = "".join(filter_parts)

    out_path = Path(output_file)
    is_mp3 = output_suffix.lower() == ".mp3"

    # minimax T2A V2 原生输出 MP3：直接写入
    # qwen Omni 原生输出 WAV：先写 WAV 再转 MP3
    if is_mp3:
        final_output = str(out_path)
    else:
        final_output = str(work_dir / "merged_output.wav")

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ac", "2",
        final_output
    ])

    ffmpeg_log = work_dir / "ffmpeg_log.txt"
    success = run_ffmpeg(cmd, str(ffmpeg_log))

    if not success:
        return False

    # qwen WAV → MP3 转码
    if is_mp3:
        pass  # minimax 原生 MP3，无额外步骤
    else:
        import shutil
        shutil.copy2(final_output, str(out_path))
        Path(final_output).unlink(missing_ok=True)

    # 清理临时文件
    for f in work_dir.iterdir():
        if f.name.startswith(("panned_", "ffmpeg_log")):
            try:
                f.unlink()
            except OSError:
                pass

    return True
