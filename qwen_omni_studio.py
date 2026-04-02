"""
Qwen Omni Studio - Qwen Omni 全流程 Fallback
单次调用完成：理解源文本 → 生成播客脚本 → 语音合成
"""
import sys
import json
import base64
import argparse
import subprocess
import logging
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel

# 共享 TTS 工具
sys.path.insert(0, str(Path(__file__).parent))
from qwen_omni_tts_tool import (
    load_api_config,
    process_segments as tts_process_segments,
)
from audio_utils import (
    stream_qwen_omni_events,
    make_wav_header,
    parse_dialogue_segments_from_text,
    VoicePool,
)

logger = logging.getLogger(__name__)
console = Console()

# ──────────────────────────────────────────────────────────────
# MODES - 复用 content_studio.py 的脚本生成模式
# ──────────────────────────────────────────────────────────────

MODES = {
    # ── 单音色模式：summary / review ──────────────────────────────
    # 单次 Omni 调用，脚本即音频，无需额外 TTS
    "summary": {
        "name": "摘要 (Qwen Omni)",
        "system": """You are a professional voice narrator / 你是一位专业资讯播音员。
IMPORTANT: Always respond in the SAME language as the user's input text. / 必须使用与输入文本相同的语言输出，切勿翻译。
Read the provided text aloud exactly as given, in a clear and concise manner.
Rules:
- Output ONLY the narration in [Narrator, neutral]: content format
- No introductions or conclusions outside the script
- The audio IS the script."""
    },
    "review": {
        "name": "评论 (Qwen Omni)",
        "system": """You are a seasoned industry critic / 你是一位资深行业评论家。
IMPORTANT: Always respond in the SAME language as the user's input text. / 必须使用与输入文本相同的语言输出，切勿翻译。
Transform the provided source into a critical review script, then read it aloud.
Rules:
- Output ONLY the review in [Expert, emotion]: content format
- Include both strengths and weaknesses constructively
- No introductions or conclusions outside the script
- The audio IS the script."""
    },

    # ── 多音色模式：deep_dive / debate ────────────────────────────
    # Omni 生成文本脚本 → segmented TTS 分角色合成 → FFmpeg 混音
    "deep_dive": {
        "name": "深入探究 (Qwen Omni)",
        "multi_voice": True,
        "system": """You are a Peabody Award-winning podcast producer / 你是一位获奖播客制作人。
IMPORTANT: Always respond in the SAME language as the user's input text. / 必须使用与输入文本相同的语言输出，切勿翻译。
Transform the provided source into a realistic multi-person dialogue script.
Rules:
- Output ONLY the spoken script in [Speaker, emotion]: content format
- No introductions, conclusions, or commentary outside the script
- No meta-commentary — just the dialogue
- Create natural conversation with friction, challenge, and resolution
- Use 2-3 distinct speakers to enrich the discussion
- Respond to the source content ONLY."""
    },
    "debate": {
        "name": "辩论 (Qwen Omni)",
        "multi_voice": True,
        "system": """You are a debate moderator / 你是一位辩论赛主席。
IMPORTANT: Always respond in the SAME language as the user's input text. / 必须使用与输入文本相同的语言输出，切勿翻译。
Transform the provided source into a structured multi-person debate script.
Rules:
- Output ONLY the debate in [Proponent, emotion]: or [Opponent, emotion]: or [Moderator, neutral]: format
- Both sides should present clear, opposing arguments
- A moderator may introduce topics and synthesize conclusions
- No introductions or conclusions outside the script
- No meta-commentary — just the debate"""
    },
}


# ──────────────────────────────────────────────────────────────
# 核心：单次 Qwen Omni 调用，同时生成脚本 + 音频
# ──────────────────────────────────────────────────────────────

def _call_qwen_omni(source_text, mode, voice, instruction, api_key, api_url):
    """
    流式调用 Qwen Omni，单次完成脚本生成 + 音频合成
    返回: (audio_bytes, script_text) 或 (None, None)
    """
    if not api_key or not api_url:
        api_key, api_url = load_api_config()

    if not api_key:
        console.print("[red]✗ 未找到 DashScope API Key[/red]")
        return None, None

    mode_config = MODES.get(mode, MODES["summary"])
    system_prompt = mode_config["system"]

    user_content = f"Source text / 源文本:\n{source_text}\n\n"
    if instruction:
        user_content += f"Specific requirement / 特别要求: {instruction}\n\n"
    user_content += "Generate the script and speak it aloud. / 生成脚本并朗读。"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen3-omni-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "modalities": ["text", "audio"],
        "audio": {
            "voice": voice,
            "format": "wav"
        },
        "stream": True,
        "stream_options": {"include_usage": True}
    }

    audio_chunks = []
    script_text = ""

    try:
        with requests.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=180,
            stream=True
        ) as resp:
            if not resp.ok:
                console.print(f"[red]✗ API 请求失败 ({resp.status_code}): {resp.text[:200]}[/red]")
                resp.raise_for_status()

            for delta in stream_qwen_omni_events(resp):
                if delta.get("content"):
                    script_text += delta["content"]
                audio_obj = delta.get("audio")
                if audio_obj and isinstance(audio_obj, dict) and audio_obj.get("data"):
                    audio_chunks.append(audio_obj["data"])

    except Exception as e:
        console.print(f"[red]✗ Qwen Omni 调用失败: {e}[/red]")
        return None, None

    if not audio_chunks:
        console.print(f"[red]✗ 响应中未包含音频数据。脚本片段: {script_text[:200]}[/red]")
        return None, None

    # 组装音频
    full_b64 = "".join(audio_chunks)
    pcm_data = bytes(base64.b64decode(full_b64))

    num_samples = len(pcm_data) // 2  # 16-bit PCM
    wav_header = make_wav_header(num_samples, sample_rate=24000, num_channels=1, bits_per_sample=16)
    audio_bytes = wav_header + pcm_data

    return audio_bytes, script_text


def _generate_script(source_text, mode, instruction, api_key, api_url):
    """
    调用 Qwen Omni 生成文本脚本（仅文本，不含音频）
    用于 deep_dive / debate 模式，脚本后续通过 segmented TTS 合成
    返回: script_text 或 None
    """
    if not api_key or not api_url:
        api_key, api_url = load_api_config()

    if not api_key:
        console.print("[red]✗ 未找到 DashScope API Key[/red]")
        return None

    mode_config = MODES.get(mode, MODES["deep_dive"])
    system_prompt = mode_config["system"]

    user_content = f"Source text / 源文本:\n{source_text}\n\n"
    if instruction:
        user_content += f"Specific requirement / 特别要求: {instruction}\n\n"
    user_content += "Generate the dialogue script only. Do not speak or read aloud — output the script text only."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen3-omni-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "modalities": ["text"],
        "stream": True,
        "stream_options": {"include_usage": True}
    }

    script_chunks = []

    try:
        with requests.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
            stream=True
        ) as resp:
            if not resp.ok:
                console.print(f"[red]✗ 脚本生成失败 ({resp.status_code}): {resp.text[:200]}[/red]")
                return None

            for delta in stream_qwen_omni_events(resp):
                if delta.get("content"):
                    script_chunks.append(delta["content"])

    except Exception as e:
        console.print(f"[red]✗ 脚本生成调用失败: {e}[/red]")
        return None

    script_text = "".join(script_chunks).strip()
    if not script_text:
        console.print("[red]✗ Omni 未返回任何脚本内容[/red]")
        return None

    return script_text


def run_multi_voice(source, mode, output_file, instruction, roles, api_key, api_url,
                    use_stereo=False, bgm_file=None, verbose=True):
    """
    多角色播客全流程：LLM 脚本生成 → 分段 TTS → FFmpeg 混音
    用于 deep_dive / debate 模式
    """
    # ── 1. 读取源 ──
    src_path = Path(source)
    if src_path.exists():
        source_text = src_path.read_text(encoding="utf-8")
    else:
        source_text = source

    if not source_text.strip():
        console.print("[red]✗ 源文本为空[/red]")
        return False

    mode_info = MODES.get(mode, MODES["deep_dive"])

    if verbose:
        console.print(Panel.fit(
            f"[bold cyan]Qwen Omni Studio - 多角色模式[/bold cyan]\n"
            f"模式: {mode_info['name']}\n"
            f"源长度: {len(source_text)} 字符\n"
            f"角色库: {list(roles.keys()) if roles else '(默认)'}"
        ))

    # ── 2. 生成对话脚本 ──
    if verbose:
        console.print("[cyan]→ 步骤 1/3：Qwen Omni 生成对话脚本...[/cyan]")

    script_text = _generate_script(
        source_text=source_text,
        mode=mode,
        instruction=instruction,
        api_key=api_key,
        api_url=api_url,
    )

    if script_text is None:
        return False

    if verbose:
        preview = script_text[:300].replace("\n", " ")
        console.print(f"[dim]生成脚本预览: {preview}...[/dim]")
        console.print("[cyan]→ 步骤 2/3：解析脚本 → 分段 TTS 合成...[/cyan]")

    # ── 3. 解析为 segments ──
    segments = parse_dialogue_segments_from_text(script_text)
    if not segments:
        console.print("[red]✗ 脚本解析失败，未找到有效片段[/red]")
        return False

    if verbose:
        unique_roles = list(dict.fromkeys(s.get("role") for s in segments))
        console.print(f"[dim]解析到 {len(segments)} 个片段，{len(unique_roles)} 个角色: {unique_roles}[/dim]")

    # ── 4. 分角色 TTS 合成 + FFmpeg 混音 ──
    if verbose:
        console.print("[cyan]→ 步骤 3/3：TTS 合成 + 混音...[/cyan]")

    # 合并 roles（命令行传入 + VoicePool 自动分配）
    final_roles = {}
    if roles:
        final_roles.update(roles)

    pool = VoicePool()
    for role_label, role_data in final_roles.items():
        if role_data.get("voice"):
            pool.assign(role_label, role_data["voice"])

    for seg in segments:
        role_label = seg["role"]
        if role_label not in final_roles:
            if pool.exhausted and verbose:
                console.print(f"[yellow]⚠ 角色超过 {len(pool._voices)} 个，音色将循环复用[/yellow]")
            final_roles[role_label] = {"voice": pool.get(role_label), "emotion": seg["emotion"]}

    success = tts_process_segments(
        segments=segments,
        output_file=output_file,
        roles=final_roles,
        use_stereo=use_stereo,
        api_key=api_key,
        api_url=api_url,
        bgm_file=bgm_file,
    )

    if success and verbose:
        console.print(f"[green]✓ 多角色播客生成成功: {output_file}[/green]")

    return success



def run_full(source, mode="deep_dive", output_file=None, instruction=None,
             voice="cherry", api_key=None, api_url=None, verbose=True,
             roles=None, use_stereo=False, bgm_file=None):
    """
    Qwen Omni 全流程

    Args:
        source: 源文本内容或文件路径
        mode: 生成模式 (deep_dive/summary/review/debate)
        output_file: 输出 MP3 文件路径
        instruction: 用户额外要求
        voice: Qwen Omni 音色（用于 summary/review 单音色模式）
        api_key / api_url: 可选，覆盖配置
        verbose: 是否打印详细日志
        roles: 角色库 dict（用于 deep_dive/debate 多音色模式）
        use_stereo: 开启立体声
        bgm_file: 背景音乐文件
    """
    # ── 多音色模式：deep_dive / debate ──
    if MODES.get(mode, {}).get("multi_voice"):
        return run_multi_voice(
            source=source,
            mode=mode,
            output_file=output_file,
            instruction=instruction,
            roles=roles or {},
            api_key=api_key,
            api_url=api_url,
            use_stereo=use_stereo,
            bgm_file=bgm_file,
            verbose=verbose,
        )

    # ── 单音色模式：summary / review ──
    src_path = Path(source)
    if src_path.exists():
        source_text = src_path.read_text(encoding="utf-8")
    else:
        source_text = source

    if not source_text.strip():
        console.print("[red]✗ 源文本为空[/red]")
        return False

    mode_info = MODES.get(mode, MODES["summary"])
    if verbose:
        console.print(Panel.fit(
            f"[bold cyan]Qwen Omni Studio (单音色模式)[/bold cyan]\n"
            f"模式: {mode_info['name']}\n"
            f"源长度: {len(source_text)} 字符\n"
            f"音色: {voice}",
            title="Qwen Omni 全流程"
        ))
        console.print("[cyan]→ 单次 Qwen Omni 调用（脚本 + 音频）...[/cyan]")

    audio_bytes, script_text = _call_qwen_omni(
        source_text=source_text,
        mode=mode,
        voice=voice,
        instruction=instruction,
        api_key=api_key,
        api_url=api_url,
    )

    if audio_bytes is None:
        return False

    if verbose:
        console.print(f"[green]✓ 音频合成成功 ({len(audio_bytes):,} bytes)[/green]")
        if script_text:
            console.print(f"[dim]生成脚本片段: {script_text[:200]}{'...' if len(script_text) > 200 else ''}[/dim]")

    # 写入文件（MP3）
    if output_file:
        out_path = Path(output_file)
        wav_path = out_path.with_suffix(".wav")
        with open(wav_path, "wb") as f:
            f.write(audio_bytes)

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav_path),
             "-codec:a", "libmp3lame", "-b:a", "128k", str(out_path)],
            capture_output=True, check=True
        )
        wav_path.unlink(missing_ok=True)

        if verbose:
            console.print(f"[green]✓ 已保存: {out_path}[/green]")

    return True


# ──────────────────────────────────────────────────────────────
# CLI 入口（独立测试用）
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Qwen Omni Studio - 全流程 Fallback 引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式:
  deep_dive  深入探究，广播级播客对话（含摩擦、突破、总结）
  summary    摘要，专业简报
  review     评论，建设性批评
  debate     辩论，正反方对辩
"""
    )
    parser.add_argument("--source", required=True, help="源文本内容或文件路径")
    parser.add_argument("--mode", default="deep_dive",
                        choices=list(MODES.keys()), help="生成模式")
    parser.add_argument("-o", "--output", default="qwen_studio_output.mp3",
                        help="输出文件路径")
    parser.add_argument("--instruction", help="额外要求")
    parser.add_argument("-v", "--voice", default="cherry",
                        help="Qwen Omni 音色")
    parser.add_argument("-r", "--roles",
                        help="角色库配置文件 (JSON)")
    parser.add_argument("--stereo", action="store_true",
                        help="开启立体声声相处理（多音色模式）")
    parser.add_argument("--bgm",
                        help="背景音乐文件路径（多音色模式）")
    parser.add_argument("-k", "--key", help="DashScope API Key")

    args = parser.parse_args()

    roles = {}
    if args.roles:
        try:
            with open(args.roles, "r") as f:
                roles = json.load(f)
        except Exception as e:
            console.print(f"[red]✗ 角色配置文件读取失败: {e}[/red]")

    success = run_full(
        source=args.source,
        mode=args.mode,
        output_file=args.output,
        instruction=args.instruction,
        voice=args.voice,
        api_key=args.key,
        roles=roles,
        use_stereo=args.stereo,
        bgm_file=args.bgm,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
