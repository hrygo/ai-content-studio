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
from pathlib import Path

import audio_utils
from audio_utils import get_duration, parse_dialogue_text, split_text, compute_role_pan_values
from config_utils import load_api_key

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


def _resolve_param(seg, role_data, key, default):
    """从 segment > role_data > default 三级解析参数（DRY helper）"""
    return seg.get(key) or role_data.get(key) or default


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
                   speed=1.0, vol=1.0, pitch=0, emotion="neutral", api_key=None, api_url=None,
                   english_normalization=False, latex_read=False, language_boost=None,
                   pronunciation_dict=None, voice_modify=None, output_format="hex"):
    """
    MiniMax TTS (T2A V2) 核心调用函数
    使用 tenacity 自动重试

    扩展参数（T2A V2 Full）:
        english_normalization: bool  英文数字规范化（改善英文数字朗读，略微增加延迟）
        latex_read: bool            LaTeX 公式朗读（需用 $$ 包裹公式）
        language_boost: str         语种增强：Chinese / English / Japanese / auto 等
        pronunciation_dict: dict      自定义读音：{"tone": ["词/读法"]}
        voice_modify: dict           声音修饰：{pitch, intensity, timbre, sound_effects}
        output_format: str           输出格式：hex（默认）或 url（24h有效）
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

    voice_setting = {
        "voice_id": voice_id,
        "speed": float(speed),
        "vol": float(vol),
        "pitch": int(pitch),
        "emotion": emotion,
    }
    if english_normalization:
        voice_setting["english_normalization"] = True
    if latex_read:
        voice_setting["latex_read"] = True

    audio_setting = {
        "sample_rate": 32000,
        "format": "mp3",
        "channel": 1,
    }

    payload = {
        "model": model,
        "text": text,
        "stream": False,
        "voice_setting": voice_setting,
        "audio_setting": audio_setting,
    }
    if language_boost:
        payload["language_boost"] = language_boost
    if pronunciation_dict:
        payload["pronunciation_dict"] = pronunciation_dict
    if voice_modify:
        payload["voice_modify"] = voice_modify
    if output_format and output_format != "hex":
        payload["output_format"] = output_format

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


def merge_audio_files(file_list, output_file, pan_list=None, bgm_file=None):
    """minimax 混音：委托 audio_utils，参数为 32kHz / work / .mp3"""
    console.print(f"[cyan]→ 混音引擎启动，处理 {len(file_list)} 个音频片段...[/cyan]")
    ok = audio_utils.merge_audio_files(
        file_list, output_file, pan_list=pan_list, bgm_file=bgm_file,
        sample_rate=32000, work_dir_name="work", output_suffix=".mp3"
    )
    if ok:
        stats["total_duration"] = get_duration(output_file)
    return ok


def process_segments(segments, output_file, roles, use_stereo=False, turn_pause=0.2,
                     api_key=None, api_url=None, bgm_file=None,
                     english_normalization=False, latex_read=False,
                     language_boost=None, pronunciation_dict=None,
                     voice_modify=None, output_format=None):
    """处理多人对话片段，支持断点续传和完整 T2A V2 参数"""
    if not segments:
        return False

    from paths import WORK_DIR
    work_dir = WORK_DIR

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
            # 扩展参数：segment > role_data > global 三级解析
            seg_en = _resolve_param(seg, role_data, "english_normalization", english_normalization)
            seg_lx = _resolve_param(seg, role_data, "latex_read", latex_read)
            seg_lb = _resolve_param(seg, role_data, "language_boost", language_boost)
            seg_pd = _resolve_param(seg, role_data, "pronunciation_dict", pronunciation_dict)
            seg_vm = _resolve_param(seg, role_data, "voice_modify", voice_modify)
            seg_of = _resolve_param(seg, role_data, "output_format", output_format)

            # 处理暂停（缓存键包含所有影响音质的参数，避免跨音色误命中）
            if turn_pause > 0 and i > 0:
                pause_key = f"pause_{turn_pause}_{voice_id}_{speed}_{vol}_{pitch}".encode()
                p_hash = hashlib.sha256(pause_key).hexdigest()[:16]
                pause_file = work_dir / f"pause_{p_hash}.mp3"
                if not (pause_file.exists() and pause_file.stat().st_size > 0):
                    ok = text_to_speech(f"<#{turn_pause}#>", str(pause_file), voice_id=voice_id,
                                        speed=speed, vol=vol, pitch=pitch,
                                        api_key=api_key, api_url=api_url)
                    if not ok:
                        console.print(f"[red]✗ 暂停片段合成失败[/red]")
                        return False
                temp_files.append(str(pause_file))
                pan_list.append(0)

            # 处理正文分段
            sub_chunks = split_text(text)
            for chunk in sub_chunks:
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
                                      api_key=api_key, api_url=api_url,
                                      english_normalization=seg_en, latex_read=seg_lx,
                                      language_boost=seg_lb, pronunciation_dict=seg_pd,
                                      voice_modify=seg_vm, output_format=seg_of):
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
    parser.add_argument("--english-normalization", action="store_true", help="英文数字规范化（仅 speech-2.8-hd/turbo）")
    parser.add_argument("--latex-read", action="store_true", help="LaTeX 公式朗读（需用 $$ 包裹）")
    parser.add_argument("--language-boost", help="语种增强：Chinese / English / Japanese 等")
    parser.add_argument("--voice-modify", help="声音修饰 JSON，例：'{\"sound_effects\":\"spacious_echo\"}'")
    parser.add_argument("--output-format", default="hex", choices=["hex", "url"], help="输出格式")

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
                                 api_key=args.key, api_url=args.api_url, bgm_file=args.bgm,
                                 english_normalization=args.english_normalization,
                                 latex_read=args.latex_read,
                                 language_boost=args.language_boost,
                                 voice_modify=json.loads(args.voice_modify) if args.voice_modify else None,
                                 output_format=args.output_format)
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
