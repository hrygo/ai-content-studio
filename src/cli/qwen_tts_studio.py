"""
Qwen TTS Studio - Qwen 专用 TTS 全流程
qwen-turbo 脚本生成 → qwen3-tts-flash 语音合成
最佳成本 + 最佳效果：49种音色，0.001元/字符
"""
import sys
import json
import argparse
import logging
from pathlib import Path

import requests
from rich.console import Console
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent))
from paths import REPO_ROOT
from qwen_tts_tool import (
    load_api_config,
    normalize_voice,
    process_segments as tts_process_segments,
    load_voice_config,
)
from audio_utils import parse_dialogue_segments_from_text

logger = logging.getLogger(__name__)
console = Console()

# ──────────────────────────────────────────────────────────────
# MODES - 脚本生成提示词（qwen-turbo 生成文本脚本）
# ──────────────────────────────────────────────────────────────

LLM_MODES = {
    "summary": {
        "name": "摘要 (Qwen TTS)",
        "system": """You are a professional voice narrator. You speak clearly and concisely.
IMPORTANT: Always respond in the SAME language as the user's input text.
Output ONLY the narration script in [Narrator, neutral]: content format.
No introductions, no conclusions, no commentary outside the script.
The audio IS the script."""
    },
    "review": {
        "name": "评论 (Qwen TTS)",
        "system": """You are a seasoned industry critic giving constructive feedback.
IMPORTANT: Always respond in the SAME language as the user's input text.
Output ONLY the review script in [Expert, neutral]: content format.
Include both strengths and weaknesses. Be balanced and insightful.
No introductions, no conclusions, no commentary outside the script.
The audio IS the script."""
    },
    "deep_dive": {
        "name": "深入探究 (Qwen TTS)",
        "system": """You are a Peabody Award-winning podcast producer creating engaging multi-person dialogue.
IMPORTANT: Always respond in the SAME language as the user's input text.
Output ONLY the spoken dialogue script in [Speaker, emotion]: content format.
Create natural conversation with 2-3 distinct speakers.
Include friction, challenge, and resolution. Make it engaging and informative.
No introductions, no conclusions, no commentary outside the script.
No meta-commentary — just the dialogue."""
    },
    "debate": {
        "name": "辩论 (Qwen TTS)",
        "system": """You are a skilled debate moderator running a structured debate.
IMPORTANT: Always respond in the SAME language as the user's input text.
Output ONLY the debate script in [Proponent, emotion]: or [Opponent, emotion]: or [Moderator, neutral]: format.
Both sides present clear, opposing arguments with evidence.
A moderator introduces topics and synthesizes conclusions.
No introductions, no conclusions, no commentary outside the script."""
    },
}


# ──────────────────────────────────────────────────────────────
# 脚本生成（qwen-turbo / qwen-plus）
# ──────────────────────────────────────────────────────────────

def generate_script(source_text, mode, instruction, api_key, api_url, model="qwen-turbo"):
    """
    调用 qwen-turbo 生成文本脚本
    返回: script_text 或 None
    """
    if not api_key or not api_url:
        api_key, api_url = load_api_config()

    if not api_key:
        console.print("[red]✗ 未找到 DashScope API Key[/red]")
        return None

    mode_config = LLM_MODES.get(mode, LLM_MODES["summary"])
    system_prompt = mode_config["system"]

    user_content = f"Source text / 源文本:\n{source_text}\n\n"
    if instruction:
        user_content += f"Specific requirement / 特别要求: {instruction}\n\n"
    user_content += "Generate the script. Do not speak aloud — output the script text only."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "max_tokens": 2048,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            f"{api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        if not response.ok:
            console.print(f"[red]✗ 脚本生成失败 ({response.status_code}): {response.text[:200]}[/red]")
            return None

        data = response.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()

        console.print(f"[red]✗ 脚本生成返回空内容[/red]")
        return None

    except Exception as e:
        console.print(f"[red]✗ 脚本生成调用失败: {e}[/red]")
        return None


# ──────────────────────────────────────────────────────────────
# 音色分配（49种音色智能映射）
# ──────────────────────────────────────────────────────────────

def assign_voices_to_segments(segments, roles, voice_config):
    """
    为每个 segment 分配 qwen 音色
    优先级：roles 配置 > role_defaults > 轮询 voice_pool
    """
    voice_pool = voice_config.get("voice_pool", [
        "Aurora", "Clara", "Terry", "Harry", "Emma", "Eric",
        "Ada", "Hannah", "Vera", "Alice", "Emily", "Dylan"
    ])
    role_defaults = voice_config.get("role_defaults", {})
    configured_roles = voice_config.get("roles", {})

    result_roles = {}
    pool_idx = 0
    warned = False

    for seg in segments:
        role_label = seg.get("role", "Narrator")
        if role_label in result_roles:
            continue

        # 1. 优先用 roles 配置
        if role_label in roles:
            v = roles[role_label].get("voice")
            if v:
                result_roles[role_label] = {"voice": normalize_voice(v)}
                continue

        # 2. 用 qwen_voices.json 中的 role_defaults
        if role_label in role_defaults:
            result_roles[role_label] = {"voice": normalize_voice(role_defaults[role_label])}
            continue

        # 3. 用 voice_pool 轮询
        voice = normalize_voice(voice_pool[pool_idx % len(voice_pool)])
        result_roles[role_label] = {"voice": voice}
        pool_idx += 1

        if pool_idx > len(voice_pool) and not warned:
            console.print(f"[yellow]⚠ 角色超过 {len(voice_pool)} 个，音色将循环复用[/yellow]")
            warned = True

    return result_roles


# ──────────────────────────────────────────────────────────────
# 全流程
# ──────────────────────────────────────────────────────────────

def run_full(source, mode="deep_dive", output_file=None, instruction=None,
             roles_path=None, use_stereo=False, bgm_file=None,
             api_key=None, api_url=None, llm_model="qwen-turbo",
             verbose=True):
    """
    Qwen TTS Studio 全流程

    Args:
        source: 源文本内容或文件路径
        mode: deep_dive / summary / review / debate
        output_file: 输出文件路径
        instruction: 用户额外要求
        roles_path: 角色库配置文件
        use_stereo: 开启立体声
        bgm_file: 背景音乐文件
        api_key / api_url: 可选覆盖配置
        llm_model: 脚本生成模型（qwen-turbo / qwen-plus）
        verbose: 是否打印详细日志
    """
    # 读取源
    src_path = Path(source)
    if src_path.exists():
        source_text = src_path.read_text(encoding="utf-8")
    else:
        source_text = source

    if not source_text.strip():
        console.print("[red]✗ 源文本为空[/red]")
        return False

    mode_info = LLM_MODES.get(mode, LLM_MODES["deep_dive"])

    if verbose:
        console.print(Panel.fit(
            f"[bold cyan]Qwen TTS Studio[/bold cyan]\n"
            f"模式: {mode_info['name']}\n"
            f"源长度: {len(source_text)} 字符\n"
            f"脚本模型: {llm_model}\n"
            f"音色库: qwen3-tts-flash (49种音色)"
        ))

    # 步骤 1: LLM 生成脚本
    if verbose:
        console.print("[cyan]→ 步骤 1/3：LLM 生成脚本...[/cyan]")

    script_text = generate_script(
        source_text=source_text,
        mode=mode,
        instruction=instruction,
        api_key=api_key,
        api_url=api_url,
        model=llm_model
    )

    if script_text is None:
        return False

    if verbose:
        preview = script_text[:300].replace("\n", " ")
        console.print(f"[dim]生成脚本预览: {preview}...[/dim]")

    # 步骤 2: 解析脚本
    if verbose:
        console.print("[cyan]→ 步骤 2/3：解析脚本...[/cyan]")

    segments = parse_dialogue_segments_from_text(script_text)
    if not segments:
        console.print("[red]✗ 脚本解析失败，未找到有效片段[/red]")
        return False

    unique_roles = list(dict.fromkeys(s.get("role") for s in segments if s.get("role")))
    if verbose:
        console.print(f"[dim]解析到 {len(segments)} 个片段，{len(unique_roles)} 个角色: {unique_roles}[/dim]")

    # 加载角色配置
    roles = {}
    if roles_path and Path(roles_path).exists():
        try:
            with open(roles_path, "r", encoding="utf-8") as f:
                roles = json.load(f)
        except Exception:
            pass

    voice_config = load_voice_config()
    final_roles = assign_voices_to_segments(segments, roles, voice_config)

    if verbose:
        assigned = {r: d.get("voice", "?") for r, d in final_roles.items()}
        console.print(f"[dim]音色分配: {assigned}[/dim]")

    # 步骤 3: TTS 合成 + 混音
    if verbose:
        console.print("[cyan]→ 步骤 3/3：TTS 合成 + 混音...[/cyan]")

    success = tts_process_segments(
        segments=segments,
        output_file=output_file,
        roles=final_roles,
        use_stereo=use_stereo,
        api_key=api_key,
        api_url=api_url,
        bgm_file=bgm_file,
        voice_config=voice_config
    )

    if success and verbose:
        console.print(f"[green]✓ Qwen TTS 生成成功: {output_file}[/green]")

    return success


# ──────────────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Qwen TTS Studio - qwen-turbo 脚本生成 + qwen3-tts-flash 语音合成",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模式:
  deep_dive  深入探究，广播级播客对话（含摩擦、突破、总结）
  summary    摘要，专业简报
  review     评论，建设性批评
  debate     辩论，正反方对辩

脚本生成模型:
  qwen-turbo   快速便宜，适合简单内容（推荐）
  qwen-plus     更高质量，适合复杂内容

示例:
  python qwen_tts_studio.py --source "内容.txt" --mode deep_dive -o out.mp3
  python qwen_tts_studio.py --source "内容.txt" --mode summary --llm-model qwen-plus -o out.mp3
"""
    )
    parser.add_argument("--source", required=True, help="源文本内容或文件路径")
    parser.add_argument("--mode", default="deep_dive",
                        choices=list(LLM_MODES.keys()), help="生成模式")
    parser.add_argument("-o", "--output", default="qwen_tts_output.mp3",
                        help="输出文件路径")
    parser.add_argument("--instruction", help="额外要求")
    parser.add_argument("-r", "--roles",
                        help="角色库配置文件 (JSON)")
    parser.add_argument("--stereo", action="store_true",
                        help="开启立体声声相处理（多音色模式）")
    parser.add_argument("--bgm", help="背景音乐文件路径")
    parser.add_argument("-k", "--key", help="DashScope API Key")
    parser.add_argument("--llm-model", default="qwen-turbo",
                        choices=["qwen-turbo", "qwen-plus", "qwen3-turbo"],
                        help="脚本生成模型")

    args = parser.parse_args()

    success = run_full(
        source=args.source,
        mode=args.mode,
        output_file=args.output,
        instruction=args.instruction,
        roles_path=args.roles,
        use_stereo=args.stereo,
        bgm_file=args.bgm,
        api_key=args.key,
        llm_model=args.llm_model,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
