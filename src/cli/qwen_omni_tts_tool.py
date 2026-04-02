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

import audio_utils
from audio_utils import (
    get_duration, run_ffmpeg, split_text, parse_dialogue_text,
    stream_qwen_omni_events, make_wav_header, compute_role_pan_values,
)
from config_utils import load_api_config

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

            for delta in stream_qwen_omni_events(resp):
                if delta.get("content"):
                    response_text += delta["content"]
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


def merge_audio_files(file_list, output_file, pan_list=None, bgm_file=None):
    """qwen 混音：委托 audio_utils，参数为 24kHz / work / 基于输出文件格式制作"""
    from pathlib import Path as _Path
    console.print(f"[cyan]→ 混音引擎启动，处理 {len(file_list)} 个音频片段...[/cyan]")
    suffix = _Path(output_file).suffix.lower()
    ok = audio_utils.merge_audio_files(
        file_list, output_file, pan_list=pan_list, bgm_file=bgm_file,
        sample_rate=24000, work_dir_name="work", output_suffix=suffix
    )
    if ok:
        stats["total_duration"] = get_duration(output_file)
    return ok


def process_segments(segments, output_file, roles, use_stereo=False,
                     api_key=None, api_url=None, bgm_file=None):
    """处理多人对话片段"""
    if not segments:
        return False

    from paths import WORK_QWEN_DIR
    work_dir = WORK_QWEN_DIR

    temp_files = []
    pan_list = []

    role_to_pan = compute_role_pan_values(list(roles.keys())) if use_stereo else {}

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
            
            sub_chunks = split_text(text)
            for chunk in sub_chunks:
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

                pan_val = role_to_pan.get(role_label, 0)
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
