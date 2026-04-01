"""
Qwen Omni TTS Tool (qwen3-omni-flash) - V2.0
基于 DashScope OpenAI 兼容接口，支持全模态原生语音生成
关键：Qwen-Omni 必须使用 stream=True 才能返回音频数据
"""
import json
import requests
import base64
import sys
import os
import argparse
import subprocess
import hashlib
import time
import logging
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()

# 统计数据
stats = {
    "tts_calls": 0,
    "cache_hits": 0,
    "total_chars": 0,
    "total_duration": 0.0,
    "errors": 0
}


def get_config_path():
    """固定指向 ~/.config/opencode/opencode.json 配置文件"""
    return os.path.expanduser("~/.config/opencode/opencode.json")


def load_api_config():
    """
    获取 DashScope (Bailian) API 配置
    优先级：1. 环境变量 2. opencode.json
    """
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    api_url = os.environ.get("DASHSCOPE_BASE_URL") or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    config_path = get_config_path()
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                bailian = config.get("provider", {}).get("bailian", {}).get("options", {})
                if not api_key or api_key == os.environ.get("DASHSCOPE_API_KEY"):
                    # 如果环境中的 key 不对或者还没设，优先用配置文件的
                    api_key = bailian.get("apiKey") or api_key
                if not api_url or api_url == "https://dashscope.aliyuncs.com/compatible-mode/v1":
                    api_url = bailian.get("baseURL") or api_url
    except Exception as e:
        logger.error(f"从配置文件读取配置失败: {e}")
    
    return api_key, api_url.rstrip("/")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def text_to_speech_qwen(text, output_file=None, voice="cherry", model="qwen3-omni-flash",
                        format="wav", system_prompt=None, api_key=None, api_url=None):
    """
    Qwen Omni TTS (via Chat Completions streaming) 核心调用函数
    关键：Qwen-Omni 必须使用 stream=True 才能返回音频数据
    音频通过 SSE 流式返回在 delta.audio.data 字段中
    """
    if not api_key or not api_url:
        k, u = load_api_config()
        api_key = api_key or k
        api_url = api_url or u

    if not api_key:
        console.print("[red]✗ 未找到 DashScope API Key。[/red]")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    else:
        # 默认系统提示词，用于稳定语音风格
        messages.append({"role": "system", "content": f"You are a professional voice-over reader. You output ONLY the exact text you are asked to read. Zero extra words. No greetings. No conclusions. No questions. Read exactly what is provided."})

    messages.append({"role": "user", "content": f"Read aloud the following text exactly, word for word, with no additions:\n{text}"})

    # 修正：qwen3-omni-flash 不支持 mp3，只支持 wav/pcm
    audio_format = "wav" if format == "mp3" else format

    payload = {
        "model": model,
        "messages": messages,
        "modalities": ["text", "audio"],
        "audio": {
            "voice": voice,
            "format": audio_format
        },
        "stream": True,
        "stream_options": {"include_usage": True}
    }

    stats["tts_calls"] += 1
    stats["total_chars"] += len(text)

    try:
        audio_chunks = []
        response_text = ""

        # 流式读取 SSE 响应
        with requests.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
            stream=True
        ) as resp:
            if not resp.ok:
                console.print(f"[red]✗ API 请求失败 ({resp.status_code}): {resp.text[:200]}[/red]")
                resp.raise_for_status()

            for line in resp.iter_lines():
                if not line or line.startswith(b":") or line.strip() == b"data: [DONE]":
                    continue
                if not line.startswith(b"data: "):
                    continue

                data_str = line.decode("utf-8")[6:].strip()
                if not data_str or data_str == "[DONE]":
                    continue

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                choices = chunk.get("choices")
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                # 收集文本
                if delta.get("content"):
                    response_text += delta["content"]

                # 收集音频 base64 数据
                audio_obj = delta.get("audio")
                if audio_obj and isinstance(audio_obj, dict) and audio_obj.get("data"):
                    audio_chunks.append(audio_obj["data"])

        if not audio_chunks:
            console.print(f"[red]✗ 响应中未包含音频数据。文本回复: {response_text[:200]}[/red]")
            stats["errors"] += 1
            return None

        # 合并所有音频分片
        full_b64 = "".join(audio_chunks)
        pcm_data = base64.b64decode(full_b64)

        # Qwen-Omni 流式返回裸 PCM 数据，需要手动构造 WAV header
        num_samples = len(pcm_data) // 2  # 16-bit PCM
        wav_header = make_wav_header(num_samples, sample_rate=24000, num_channels=1, bits_per_sample=16)
        audio_bytes = wav_header + pcm_data

        if output_file:
            out_path = Path(output_file)
            if out_path.suffix.lower() == ".mp3":
                # 先写 WAV，再转 MP3
                wav_path = out_path.with_suffix(".wav")
                with open(wav_path, "wb") as f:
                    f.write(audio_bytes)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_path),
                     "-codec:a", "libmp3lame", "-b:a", "128k", str(out_path)],
                    capture_output=True, check=True
                )
                wav_path.unlink(missing_ok=True)
                out_path = out_path
            else:
                with open(out_path, "wb") as f:
                    f.write(audio_bytes)

        console.print(f"[green]✓ 合成成功 ({len(audio_bytes):,} bytes, {len(response_text)} chars)[/green]")
        if response_text:
            console.print(f"[dim]文本回复: {response_text[:100]}{'...' if len(response_text) > 100 else ''}[/dim]")

        return audio_bytes

    except Exception as e:
        stats["errors"] += 1
        logger.error(f"API 调用失败: {e}")
        raise


def get_duration(file_path):
    """获取音频文件时长 (秒)"""
    abs_path = os.path.abspath(file_path)
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        abs_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(output)
    except Exception as e:
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


def merge_audio_files(file_list, output_file, pan_list=None, bgm_file=None):
    """音频混音引擎 (复用 Minimax 逻辑)"""
    if not file_list:
        return False

    work_dir = Path(__file__).parent / "work_qwen"
    work_dir.mkdir(exist_ok=True)

    console.print(f"[cyan]→ 混音引擎启动，处理 {len(file_list)} 个音频片段...[/cyan]")

    processed_list = []
    if pan_list and len(pan_list) == len(file_list):
        for i, (f, balance) in enumerate(zip(file_list, pan_list)):
            if balance == 0:
                processed_list.append(f)
                continue
            l_vol = 1.0 if balance <= 0 else max(0.1, 1.0 - balance)
            r_vol = 1.0 if balance >= 0 else max(0.1, 1.0 + balance)
            panned_temp = work_dir / f"panned_{i}.wav"
            cmd = [
                "ffmpeg", "-y", "-i", f,
                "-af", f"pan=stereo|c0={l_vol:.1f}*c0|c1={r_vol:.1f}*c0",
                str(panned_temp)
            ]
            subprocess.run(cmd, capture_output=True)
            processed_list.append(str(panned_temp))
    else:
        processed_list = file_list

    inputs = []
    filter_parts = []
    current_time_ms = 0

    for i, f in enumerate(processed_list):
        inputs.extend(["-i", f])
        overlap_ms = 150 if i > 0 else 0
        delay = max(0, current_time_ms - overlap_ms)
        filter_parts.append(f"[{i}:a]adelay={delay}|{delay}[a{i}];")
        duration = get_duration(f)
        current_time_ms += int(duration * 1000)

    amix_inputs = "".join([f"[a{i}]" for i in range(len(processed_list))])
    master_v = f"{amix_inputs}amix=inputs={len(processed_list)}:duration=first,"
    master_v += "acompressor=threshold=-15dB:ratio=4:attack=5:release=50,"
    master_v += "alimiter=limit=-1.0dB,"
    master_v += "loudnorm=I=-16:TP=-1.5:LRA=11"

    filter_parts.append(f"{master_v}[mixed_voice];")

    if bgm_file and os.path.exists(bgm_file):
        inputs.extend(["-i", bgm_file])
        bgm_idx = len(processed_list)
        filter_parts.append(
            f"[{bgm_idx}:a]volume=0.15,acompressor=threshold=-40dB:ratio=20:attack=5:release=200[bgm_ducked];"
            f"[mixed_voice][bgm_ducked]amix=inputs=2:duration=first[out]"
        )
    else:
        filter_parts.append("[mixed_voice]volume=1.0[out]")

    filter_complex = "".join(filter_parts)

    out_path = Path(output_file)
    is_mp3 = out_path.suffix.lower() == ".mp3"
    final_output = output_file
    if is_mp3:
        # 混音阶段统一输出 WAV，再统一转换
        final_output = str(work_dir / "merged_output.wav")

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ac", "2",
        "-ab", "128k",
        final_output
    ])

    ffmpeg_log = work_dir / "ffmpeg_log.txt"
    success = run_ffmpeg(cmd, str(ffmpeg_log))

    if not success:
        console.print("[red]✗ FFmpeg 混音失败！[/red]")
        return False

    # MP3 转换
    if is_mp3:
        subprocess.run(
            ["ffmpeg", "-y", "-i", final_output,
             "-codec:a", "libmp3lame", "-b:a", "128k", output_file],
            capture_output=True, check=True
        )
        Path(final_output).unlink(missing_ok=True)

    stats["total_duration"] = get_duration(output_file)
    return True


def split_text(text, max_len=300):
    """智能文本切分"""
    if len(text) <= max_len:
        return [text]
    delimiters = ["。", "！", "？", "；", ".", "!", "?", ";", "\n"]
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
                final_chunks.append(c[i:i+max_len])
        else:
            final_chunks.append(c)
    return final_chunks


def make_wav_header(num_samples, sample_rate=24000, num_channels=1, bits_per_sample=16):
    """构造 PCM 数据的 WAV header"""
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align

    import struct
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,          # fmt chunk size
        1,           # audio format (PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header


def parse_dialogue_text(file_path):
    """解析对话格式文本"""
    import re
    segments = []
    # 匹配格式: [角色, 情感]: 内容
    pattern = re.compile(r"\[(.*?)(?:,\s*(.*?))?\]:\s*(.*)")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                match = pattern.match(line)
                if match:
                    segments.append({
                        "role": match.group(1).strip(),
                        "emotion": match.group(2).strip() if match.group(2) else "neutral",
                        "text": match.group(3).strip()
                    })
                else:
                    segments.append({"text": line, "role": "Narrator"})
    except Exception as e:
        logger.error(f"解析对话文本失败: {e}")
    return segments


def process_segments(segments, output_file, roles, use_stereo=False, turn_pause=0.2,
                     api_key=None, api_url=None, bgm_file=None):
    """处理多人对话片段"""
    if not segments:
        return False

    work_dir = Path(__file__).parent / "work_qwen"
    work_dir.mkdir(exist_ok=True)

    temp_files = []
    pan_list = []

    role_to_pan = {}
    if use_stereo:
        unique_roles = list(roles.keys())
        for i, role in enumerate(unique_roles):
            if len(unique_roles) == 1:
                role_to_pan[role] = 0
            else:
                role_to_pan[role] = -0.8 + (1.6 * i / (len(unique_roles)-1))

    total_segs = len(segments)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Qwen Omni 合成音频片段...", total=total_segs)

        for i, seg in enumerate(segments):
            role_label = seg.get("role")
            role_data = roles.get(role_label, {})
            text = seg.get("text", "")
            voice = seg.get("voice") or role_data.get("voice") or "cherry"
            emotion = seg.get("emotion") or role_data.get("emotion") or "neutral"
            
            role_prompt = (
                f"You are a professional voice-over reader as {role_label} ({emotion} emotion). "
                f"Read aloud the text exactly, word for word. "
                f"Output ONLY the text you are asked to read. "
                f"Zero extra words. No greetings. No conclusions. No questions."
            )
            if role_data.get("personality"):
                role_prompt = role_data["personality"] + " " + role_prompt
            
            # 处理正文分段
            sub_chunks = split_text(text)
            for j, chunk in enumerate(sub_chunks):
                # 缓存键：文本 + 声音 + 情感 + 角色描述
                seg_key = f"qwen_{voice}_{chunk}_{emotion}_{role_label}".encode()
                seg_hash = hashlib.sha256(seg_key).hexdigest()[:16]
                # 缓存统一用 wav，后续按需转换
                temp_name = work_dir / f"qwen_seg_{seg_hash}.wav"

                progress.update(task, description=f"[cyan][{i+1}/{total_segs}] {role_label}({voice}): {chunk[:30]}...")

                if temp_name.exists() and temp_name.stat().st_size > 0:
                    stats["cache_hits"] += 1
                    temp_files.append(str(temp_name))
                else:
                    if text_to_speech_qwen(text=chunk, output_file=str(temp_name), voice=voice,
                                          system_prompt=role_prompt, api_key=api_key, api_url=api_url,
                                          format="wav"):
                        temp_files.append(str(temp_name))
                    else:
                        console.print(f"[red]✗ 分片合成失败[/red]")
                        return False

                pan_val = role_to_pan.get(role_label, 0) if use_stereo else 0
                pan_list.append(pan_val)

            progress.advance(task)

    if not temp_files:
        return False

    return merge_audio_files(temp_files, output_file, pan_list if use_stereo else None, bgm_file=bgm_file)


def print_summary():
    """打印执行摘要"""
    console.print(Panel.fit(
        f"[bold cyan]Qwen Omni TTS 执行摘要[/bold cyan]\n\n"
        f"TTS 调用次数: {stats['tts_calls']}\n"
        f"缓存命中: {stats['cache_hits']}\n"
        f"总字符数: {stats['total_chars']}\n"
        f"总时长: {stats['total_duration']:.2f} 秒\n"
        f"错误数: {stats['errors']}",
        title="统计信息"
    ))


def main():
    parser = argparse.ArgumentParser(description="Qwen Omni (qwen3-omni-flash) 语音合成工具")
    parser.add_argument("text", nargs="?", help="待合成文本")
    parser.add_argument("-s", "--source", help="数据源 (JSON 列表或对话 TXT)")
    parser.add_argument("-r", "--roles", help="角色库配置文件 (JSON)")
    parser.add_argument("-k", "--key", help="DashScope API Key")
    parser.add_argument("--api-url", help="DashScope API URL (OpenAI 兼容端点)")
    parser.add_argument("--stereo", action="store_true", help="开启立体声声相处理")
    parser.add_argument("--bgm", help="背景音乐文件路径")
    parser.add_argument("-o", "--output", default="qwen_output.wav", help="输出文件路径")
    parser.add_argument("-v", "--voice", default="cherry",
                        help="音色 (qwen3-omni-flash 账户可用: cherry/ethan/chelsie; 完整列表见 https://help.aliyun.com/zh/model-studio/omni-voice-list)")
    parser.add_argument("-m", "--model", default="qwen3-omni-flash", help="模型名称")

    args = parser.parse_args()

    if args.source:
        roles = {}
        if args.roles:
            try:
                with open(args.roles, "r") as f:
                    roles = json.load(f)
            except:
                pass

        segments = []
        if args.source.endswith(".json"):
            try:
                with open(args.source, "r") as f:
                    segments = json.load(f)
            except:
                pass
        else:
            segments = parse_dialogue_text(args.source)

        success = process_segments(segments, args.output, roles,
                                   use_stereo=args.stereo,
                                   api_key=args.key, api_url=args.api_url, bgm_file=args.bgm)
        print_summary()
        sys.exit(0 if success else 1)

    elif args.text:
        text_to_speech_qwen(text=args.text, output_file=args.output, voice=args.voice,
                           model=args.model, api_key=args.key, api_url=args.api_url)
        print_summary()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
