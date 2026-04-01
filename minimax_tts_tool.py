"""
MiniMax TTS 专业型工具 (T2A V2 Pro) - V5.0
使用 tenacity 重试，rich 可观测性，保持文件缓存
"""
import json
import requests
import binascii
import sys
import os
import argparse
import subprocess
import hashlib
import time
import shlex
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()

# 统计数据（用于可观测性）
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


def load_api_key():
    """
    获取 MiniMax API Key
    优先级：1. 环境变量 2. opencode.json
    """
    env_key = os.environ.get("MINIMAX_TTS_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    if env_key:
        return env_key

    config_path = get_config_path()
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                return config.get("provider", {}).get("minimax", {}).get("options", {}).get("apiKey")
    except Exception as e:
        logger.error(f"从配置文件读取 Key 失败: {e}")
    return None


def get_api_url():
    """获取 MiniMax TTS API URL"""
    url = os.environ.get("MINIMAX_TTS_API_URL") or os.environ.get("MINIMAX_API_URL") or os.environ.get("MINIMAX_BASE_URL")
    if url:
        return url
    return "https://api.minimaxi.com/v1/t2a_v2"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def text_to_speech(text, output_file=None, voice_id="male-qn-qingse", model="speech-2.8-hd",
                   speed=1.0, vol=1.0, pitch=0, emotion="neutral", api_key=None, api_url=None):
    """
    MiniMax TTS (T2A V2) 核心调用函数
    使用 tenacity 自动重试
    """
    if not api_key:
        api_key = load_api_key()

    if not api_key:
        console.print("[red]✗ 未找到 MiniMax API Key。[/red]")
        return None

    actual_url = api_url or get_api_url()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": {
            "voice_id": voice_id,
            "speed": speed,
            "vol": vol,
            "pitch": pitch,
            "emotion": emotion
        },
        "audio_setting": {
            "sample_rate": 32000,
            "format": "mp3",
            "channel": 1
        }
    }

    stats["tts_calls"] += 1
    stats["total_chars"] += len(text)

    try:
        response = requests.post(actual_url, headers=headers, json=payload, timeout=30)

        if response.status_code == 429:
            raise requests.exceptions.RequestException("Rate limited (429)")

        response.raise_for_status()
        res_data = response.json()

        base_resp = res_data.get("base_resp", {})
        status_code = base_resp.get("status_code")

        if status_code in [1001, 1013, 1021]:
            raise requests.exceptions.RequestException(f"Business rate limited ({status_code})")

        if status_code != 0:
            console.print(f"[red]✗ 接口返回错误码: {status_code}[/red]")
            stats["errors"] += 1
            return None

        audio_hex = res_data.get("data", {}).get("audio")
        if not audio_hex:
            console.print(f"[red]✗ 响应中未包含音频数据[/red]")
            stats["errors"] += 1
            return None

        audio_bytes = binascii.unhexlify(audio_hex)

        if output_file:
            with open(output_file, "wb") as f:
                f.write(audio_bytes)

        return audio_bytes

    except binascii.Error as e:
        console.print(f"[red]✗ 音频数据解码失败: {e}[/red]")
        stats["errors"] += 1
        return None
    except Exception as e:
        stats["errors"] += 1
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
        logger.error(f"无法读取时长: {file_path}, Error: {e}")
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
    """V5 Studio Pro 混音引擎"""
    if not file_list:
        return False

    work_dir = Path(__file__).parent / "work"
    work_dir.mkdir(exist_ok=True)

    console.print(f"[cyan]→ 混音引擎启动，处理 {len(file_list)} 个音频片段...[/cyan]")

    processed_list = []
    if pan_list and len(pan_list) == len(file_list):
        console.print("[cyan]  进行声道空间处理 (Stereo Panning)...[/cyan]")
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

    console.print("[cyan]  编排并行音轨 (Parallel Mixing)...[/cyan]")
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
        console.print(f"[cyan]  混入背景音乐: {bgm_file}...[/cyan]")
        inputs.extend(["-i", bgm_file])
        bgm_idx = len(processed_list)
        filter_parts.append(
            f"[{bgm_idx}:a]volume=0.15,acompressor=threshold=-40dB:ratio=20:attack=5:release=200[bgm_ducked];"
            f"[mixed_voice][bgm_ducked]amix=inputs=2:duration=first[out]"
        )
    else:
        filter_parts.append("[mixed_voice]volume=1.0[out]")

    filter_complex = "".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-ac", "2",
        "-ab", "128k",
        output_file
    ])

    ffmpeg_log = work_dir / "ffmpeg_log.txt"
    success = run_ffmpeg(cmd, str(ffmpeg_log))

    if not success:
        console.print("[red]✗ FFmpeg 混音失败！[/red]")
        with open(ffmpeg_log, "r") as f:
            print(f.read())
        return False

    # 清理临时文件
    for f in work_dir.iterdir():
        if f.name.startswith(("panned_", "ffmpeg_log")):
            try:
                f.unlink()
            except:
                pass

    stats["total_duration"] = get_duration(output_file)
    return True


def split_text(text, max_len=300):
    """按标点符号智能切分长文本"""
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


def parse_dialogue_text(file_path):
    """解析对话格式文本"""
    import re
    segments = []
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
    """处理多人对话片段，支持断点续传"""
    if not segments:
        return False

    work_dir = Path(__file__).parent / "work"
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
        task = progress.add_task("[cyan]合成音频片段...", total=total_segs)

        for i, seg in enumerate(segments):
            role_label = seg.get("role")
            role_data = roles.get(role_label, {})
            text = seg.get("text", "")
            voice_id = seg.get("voice_id") or role_data.get("voice_id") or "male-qn-qingse"
            emotion = seg.get("emotion") or role_data.get("emotion") or "neutral"
            speed = seg.get("speed") or role_data.get("speed") or 1.0
            vol = seg.get("vol") or role_data.get("vol") or 1.0
            pitch = seg.get("pitch") or role_data.get("pitch") or 0

            # 处理暂停
            if turn_pause > 0 and i > 0:
                pause_key = f"pause_{turn_pause}_{voice_id}".encode()
                p_hash = hashlib.sha256(pause_key).hexdigest()[:16]
                pause_file = work_dir / f"pause_{p_hash}.mp3"
                if not (pause_file.exists() and pause_file.stat().st_size > 0):
                    text_to_speech(f"<#{turn_pause}#>", str(pause_file), voice_id=voice_id, api_key=api_key, api_url=api_url)
                temp_files.append(str(pause_file))
                pan_list.append(0)

            # 处理正文分段
            sub_chunks = split_text(text)
            for j, chunk in enumerate(sub_chunks):
                seg_key = f"{voice_id}_{chunk}_{speed}_{vol}_{pitch}_{emotion}".encode()
                seg_hash = hashlib.sha256(seg_key).hexdigest()[:16]
                temp_name = work_dir / f"seg_{seg_hash}.mp3"

                progress.update(task, description=f"[cyan][{i+1}/{total_segs}] {role_label}: {chunk[:30]}...")

                if temp_name.exists() and temp_name.stat().st_size > 0:
                    stats["cache_hits"] += 1
                    temp_files.append(str(temp_name))
                else:
                    if text_to_speech(text=chunk, output_file=str(temp_name), voice_id=voice_id,
                                      speed=speed, vol=vol, pitch=pitch, emotion=emotion,
                                      api_key=api_key, api_url=api_url):
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
    """打印执行摘要面板"""
    console.print(Panel.fit(
        f"[bold cyan]TTS 执行摘要[/bold cyan]\n\n"
        f"TTS 调用次数: {stats['tts_calls']}\n"
        f"缓存命中: {stats['cache_hits']}\n"
        f"总字符数: {stats['total_chars']}\n"
        f"总时长: {stats['total_duration']:.2f} 秒\n"
        f"错误数: {stats['errors']}",
        title="统计信息"
    ))


def main():
    parser = argparse.ArgumentParser(description="MiniMax 语音合成专业型工具 (T2A V2 Pro V5.0)")
    parser.add_argument("text", nargs="?", help="待合成文本")
    parser.add_argument("-s", "--source", help="数据源 (JSON 列表或对话 TXT)")
    parser.add_argument("-r", "--roles", help="角色库配置文件 (JSON)")
    parser.add_argument("-k", "--key", help="MiniMax API Key")
    parser.add_argument("--api-url", help="MiniMax API URL")
    parser.add_argument("-p", "--pause", type=float, default=0.2, help="角色切换停顿时间 (秒)")
    parser.add_argument("--stereo", action="store_true", help="开启立体声声相处理")
    parser.add_argument("--bgm", help="背景音乐文件路径")
    parser.add_argument("-o", "--output", default="output.mp3", help="输出文件路径")
    parser.add_argument("-v", "--voice", default="male-qn-qingse", help="默认音色")
    parser.add_argument("-e", "--emotion", default="neutral", help="默认情感")

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
                                   use_stereo=args.stereo, turn_pause=args.pause,
                                   api_key=args.key, api_url=args.api_url, bgm_file=args.bgm)
        print_summary()
        sys.exit(0 if success else 1)

    elif args.text:
        text_to_speech(text=args.text, output_file=args.output, voice_id=args.voice,
                       emotion=args.emotion, api_key=args.key, api_url=args.api_url)
        print_summary()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
