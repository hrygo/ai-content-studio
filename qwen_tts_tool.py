"""
Qwen TTS Tool (qwen3-tts-flash) - 专用语音合成引擎
阿里云百炼 qwen3-tts-flash：49种音色 + 8大方言，0.001元/字符

关键：qwen-tts-flash 使用独立 API 端点（非 Chat Completions）
"""
import json
import requests
import base64
import sys
import argparse
import subprocess
import hashlib
import struct
import logging
from pathlib import Path

import audio_utils
from audio_utils import get_duration, split_text, parse_dialogue_text, merge_audio_files, compute_role_pan_values
from config_utils import load_api_config as _load_qwen_tts_config

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

console = Console()

stats = {
    "tts_calls": 0,
    "cache_hits": 0,
    "total_chars": 0,
    "total_duration": 0.0,
    "errors": 0
}

# 音色名称标准化映射（统一转为小写，API 需要小写音色名）
_VOICE_ALIASES = {
    v: v.lower() for v in [
        "Aurora", "Nannuann", "Clara", "Terri", "Harry", "Eric", "Emma",
        "Ada", "Alice", "Emily", "Hannah", "Cherry", "Vera", "Bella", "Luna",
        "Lily", "Ruby", "Coco", "Andy", "Amy", "Daisy", "Sophia",
        "Dylan", "Jada", "Sunny",
    ]
}
# 确保小写 key 也能用
_VOICE_ALIASES.update({
    v.lower(): v.lower() for v in _VOICE_ALIASES.values()
})


def load_api_config():
    """qwen3-tts-flash API 配置（qwen_tts_tool 专用端点）"""
    return _load_qwen_tts_config()


def load_voice_config():
    """加载 qwen voices 配置"""
    config_path = Path(__file__).parent / "configs" / "qwen_voices.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def normalize_voice(voice):
    """标准化音色名称"""
    if not voice:
        return "Aurora"
    lower = voice.lower()
    return _VOICE_ALIASES.get(lower, voice)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def text_to_speech(text, output_file=None, voice="Aurora", speed=1.0,
                   language="Auto", api_key=None, api_url=None, model="qwen3-tts-flash"):
    """
    Qwen TTS (qwen3-tts-flash) 核心调用函数
    使用流式 SSE 响应，支持实时接收音频分片
    """
    if not api_key or not api_url:
        k, u = load_api_config()
        api_key = api_key or k
        api_url = api_url or u

    if not api_key:
        console.print("[red]✗ 未找到 DashScope API Key。[/red]")
        return None

    voice = normalize_voice(voice)
    # qwen-tts API 使用小写音色名（如 aurora, cherry）
    voice_id = voice.lower()

    # qwen-tts-flash 使用独立 API 端点（不是 /compatible-mode/v1/chat/completions）
    base_url = api_url.replace("/compatible-mode/v1", "").rstrip("/")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-SSE": "enable"
    }

    payload = {
        "model": model,
        "input": {
            "text": text,
            "voice": voice_id,
            "language_type": language if language != "Auto" else "Auto"
        }
    }

    stats["tts_calls"] += 1
    stats["total_chars"] += len(text)

    try:
        resp = requests.post(
            f"{base_url}/api/v1/services/aigc/multimodal-generation/generation",
            headers=headers,
            json=payload,
            timeout=60,
            stream=True
        )
        audio_base64_chunks = []

        # 先检查状态码（不在此处消费 body）
        if resp.status_code != 200:
            console.print(f"[red]✗ API 请求失败 ({resp.status_code}): {resp.text[:200]}[/red]")
            resp.raise_for_status()

        raw_lines = [l.decode("utf-8", errors="replace") for l in resp.iter_lines() if l]
        for ls in raw_lines:
            if not ls.startswith("data:"):
                continue
            chunk_str = ls[5:].strip()
            if not chunk_str:
                continue
            try:
                chunk = json.loads(chunk_str)
                audio_obj = chunk.get("output", {}).get("audio", {})
                audio_data = audio_obj.get("data")
                if audio_data:
                    audio_base64_chunks.append(audio_data)
            except json.JSONDecodeError:
                continue

        if not audio_base64_chunks:
            console.print(f"[red]✗ 响应中未包含音频数据[/red]")
            stats["errors"] += 1
            return None

        # 合并所有音频分片
        full_b64 = "".join(audio_base64_chunks)
        audio_bytes = base64.b64decode(full_b64)

        if output_file:
            out_path = Path(output_file)
            if out_path.suffix.lower() == ".mp3":
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

        console.print(f"[green]✓ 合成成功 ({len(audio_bytes):,} bytes, {len(text)} chars)[/green]")
        return audio_bytes

    except Exception as e:
        stats["errors"] += 1
        logger.error(f"API 调用失败: {e}")
        raise


def merge_audio_files(file_list, output_file, pan_list=None, bgm_file=None):
    """qwen 混音：委托 audio_utils，参数为 16kHz / work_tts / 基于输出格式"""
    from pathlib import Path as _Path
    console.print(f"[cyan]→ 混音引擎启动，处理 {len(file_list)} 个音频片段...[/cyan]")
    suffix = _Path(output_file).suffix.lower()
    ok = audio_utils.merge_audio_files(
        file_list, output_file, pan_list=pan_list, bgm_file=bgm_file,
        sample_rate=16000, work_dir_name="work_tts", output_suffix=suffix
    )
    if ok:
        stats["total_duration"] = get_duration(output_file)
    return ok


def process_segments(segments, output_file, roles, use_stereo=False,
                     api_key=None, api_url=None, bgm_file=None, voice_config=None):
    """
    处理多人对话片段，支持 qwen 49种音色
    roles 格式: {"角色名": {"voice": "Aurora", "speed": 1.0, ...}}
    voice_config: qwen_voices.json 完整配置
    """
    if not segments:
        return False

    voice_cfg = voice_config or load_voice_config()
    voice_pool = voice_cfg.get("voice_pool", ["cherry", "ethan", "chelsie"])
    role_defaults = voice_cfg.get("role_defaults", {})

    work_dir = Path(__file__).parent / "work_tts"
    work_dir.mkdir(exist_ok=True)

    temp_files = []
    pan_list = []

    role_to_pan = compute_role_pan_values(
        list(dict.fromkeys(s.get("role") for s in segments if s.get("role")))
    ) if use_stereo else {}

    total_segs = len(segments)
    pool_idx = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Qwen TTS 合成音频片段...", total=total_segs)

        for i, seg in enumerate(segments):
            role_label = seg.get("role", "Narrator")
            text = seg.get("text", "")
            if not text:
                progress.advance(task)
                continue

            role_data = roles.get(role_label, {})
            seg_voice = seg.get("voice") or role_data.get("voice")

            # 自动分配音色（角色未在 roles 中定义时）
            if not seg_voice:
                if role_label in role_defaults:
                    seg_voice = role_defaults[role_label]
                else:
                    seg_voice = voice_pool[pool_idx % len(voice_pool)]
                    pool_idx += 1

            seg_voice = normalize_voice(seg_voice)
            speed = float(seg.get("speed") or role_data.get("speed") or 1.0)

            # 文本分段（TTS 最大 512 tokens ≈ ~350-400 字符）
            sub_chunks = split_text(text, max_len=350)
            for chunk in sub_chunks:
                seg_key = f"qwen_{seg_voice}_{chunk}_{speed}".encode()
                seg_hash = hashlib.sha256(seg_key).hexdigest()[:16]
                suffix = ".wav"
                temp_name = work_dir / f"qwen_seg_{seg_hash}{suffix}"

                progress.update(
                    task,
                    description=f"[cyan][{i+1}/{total_segs}] {role_label}({seg_voice}): {chunk[:25]}..."
                )

                if temp_name.exists() and temp_name.stat().st_size > 0:
                    stats["cache_hits"] += 1
                    temp_files.append(str(temp_name))
                else:
                    if text_to_speech(
                        text=chunk,
                        output_file=str(temp_name),
                        voice=seg_voice,
                        speed=speed,
                        api_key=api_key,
                        api_url=api_url
                    ):
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
        f"[bold cyan]Qwen TTS 执行摘要[/bold cyan]\n\n"
        f"TTS 调用次数: {stats['tts_calls']}\n"
        f"缓存命中: {stats['cache_hits']}\n"
        f"总字符数: {stats['total_chars']}\n"
        f"总时长: {stats['total_duration']:.2f} 秒\n"
        f"错误数: {stats['errors']}",
        title="统计信息"
    ))


def main():
    parser = argparse.ArgumentParser(description="Qwen TTS 专用语音合成工具 (qwen3-tts-flash)")
    parser.add_argument("text", nargs="?", help="待合成文本")
    parser.add_argument("-s", "--source", help="数据源 (JSON 列表或对话 TXT)")
    parser.add_argument("-r", "--roles", help="角色库配置文件 (JSON)")
    parser.add_argument("-k", "--key", help="DashScope API Key")
    parser.add_argument("--api-url", help="DashScope API URL")
    parser.add_argument("--stereo", action="store_true", help="开启立体声声相处理")
    parser.add_argument("--bgm", help="背景音乐文件路径")
    parser.add_argument("-o", "--output", default="qwen_tts_output.wav", help="输出文件路径")
    parser.add_argument("-v", "--voice", default="Aurora", help="音色名称")
    parser.add_argument("-m", "--model", default="qwen3-tts-flash", help="模型名称")

    args = parser.parse_args()

    if args.source:
        roles = {}
        voice_cfg = {}
        if args.roles:
            try:
                with open(args.roles, "r") as f:
                    roles = json.load(f)
            except Exception:
                pass
        else:
            cfg_path = Path(__file__).parent / "configs" / "qwen_voices.json"
            if cfg_path.exists():
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        voice_cfg = json.load(f)
                        roles = voice_cfg.get("roles", {})
                except Exception:
                    pass

        segments = []
        if args.source.endswith(".json"):
            try:
                with open(args.source, "r") as f:
                    segments = json.load(f)
            except Exception:
                pass
        else:
            segments = parse_dialogue_text(args.source)

        success = process_segments(
            segments, args.output, roles,
            use_stereo=args.stereo,
            api_key=args.key, api_url=args.api_url,
            bgm_file=args.bgm, voice_config=voice_cfg
        )
        print_summary()
        sys.exit(0 if success else 1)

    elif args.text:
        text_to_speech(
            text=args.text,
            output_file=args.output,
            voice=args.voice,
            api_key=args.key,
            api_url=args.api_url,
            model=args.model
        )
        print_summary()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
