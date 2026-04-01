"""
Studio Orchestrator - 统一编排器
MiniMax Content Studio 优先，Qwen Omni 全流程 Fallback
"""
import os
import sys
import json
import argparse
import subprocess
import time
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent))

from minimax_tts_tool import load_api_key as load_minimax_key
from qwen_omni_tts_tool import load_api_config as load_qwen_config

logger = logging.getLogger(__name__)
console = Console()

DIR = Path(__file__).parent
PROCESSOR_SCRIPT = DIR / "content_studio.py"
MINIMAX_TTS = DIR / "minimax_tts_tool.py"
QWEN_STUDIO = DIR / "qwen_omni_studio.py"
OUTPUTS_DIR = DIR / "outputs"
WORK_DIR = DIR / "work"

OUTPUTS_DIR.mkdir(exist_ok=True)
WORK_DIR.mkdir(exist_ok=True)


# ──────────────────────────────────────────────────────────────
# 引擎可用性检测
# ──────────────────────────────────────────────────────────────

def check_engines():
    """检测所有引擎状态"""
    minimax_llm = load_minimax_key() is not None
    minimax_tts = load_minimax_key() is not None
    qwen_cfg = load_qwen_config()
    qwen_ok = qwen_cfg[0] is not None and qwen_cfg[1] is not None

    return {
        "minimax_studio": minimax_llm and minimax_tts,
        "qwen_omni_studio": qwen_ok,
    }


def print_engine_status():
    """打印引擎状态"""
    engs = check_engines()
    rows = []
    for name, available in engs.items():
        label = name.replace("_", " ").title()
        rows.append(f"{'✓' if available else '✗'} {label}: {'可用' if available else '未配置'}")

    console.print(Panel.fit(
        "\n".join(rows),
        title="[bold]引擎状态[/bold]",
        border_style="cyan"
    ))


# ──────────────────────────────────────────────────────────────
# MiniMax Studio 流程
# ──────────────────────────────────────────────────────────────

def run_minimax_studio(source, mode, output, instruction, roles_path,
                        stereo, bgm, llm_url, tts_url):
    """
    运行 MiniMax Content Studio 完整流程：
    content_studio.py (LLM) → minimax_tts_tool.py (TTS)
    成功返回 True，失败抛出异常
    """
    script_file = OUTPUTS_DIR / "generated_script.txt"

    # 步骤 1: LLM 生成脚本
    console.print("\n[bold yellow]步骤 1/2:[/yellow] [cyan]MiniMax LLM 生成脚本...[/cyan]")

    env = dict(os.environ)
    if llm_url:
        env["MINIMAX_LLM_API_URL"] = llm_url

    cmd_llm = [
        sys.executable, str(PROCESSOR_SCRIPT),
        "--source", source,
        "--mode", mode,
        "--output", str(script_file),
    ]
    if instruction:
        cmd_llm += ["--instruction", instruction]

    proc = subprocess.run(cmd_llm, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"LLM 脚本生成失败: {proc.stderr or proc.stdout}")

    console.print(f"[green]✓ 脚本生成完成[/green]")

    # 步骤 2: MiniMax TTS 合成
    console.print("\n[bold yellow]步骤 2/2:[/yellow] [cyan]MiniMax TTS 语音合成...[/cyan]")

    tts_env = dict(os.environ)
    if tts_url:
        tts_env["MINIMAX_TTS_API_URL"] = tts_url

    tts_cmd = [
        sys.executable, str(MINIMAX_TTS),
        "-s", str(script_file),
        "-r", str(roles_path),
        "-o", output,
    ]
    if stereo:
        tts_cmd.append("--stereo")
    if bgm:
        tts_cmd += ["--bgm", bgm]

    proc = subprocess.run(tts_cmd, capture_output=True, text=True, env=tts_env)
    if proc.returncode != 0:
        raise RuntimeError(f"MiniMax TTS 合成失败: {proc.stderr or proc.stdout}")

    console.print(f"[green]✓ 语音合成完成[/green]")
    return True


# ──────────────────────────────────────────────────────────────
# Qwen Omni Studio 流程
# ──────────────────────────────────────────────────────────────

def run_qwen_studio(source, mode, output, instruction, voice):
    """运行 Qwen Omni 全流程 Fallback"""
    console.print("\n[bold yellow]→ 切换到 Qwen Omni Studio (Fallback)...[/bold yellow]")
    from qwen_omni_studio import run_full
    return run_full(
        source=source,
        mode=mode,
        output_file=output,
        instruction=instruction,
        voice=voice,
        verbose=True,
    )


# ──────────────────────────────────────────────────────────────
# 主编排逻辑
# ──────────────────────────────────────────────────────────────

def run(source, mode, output, instruction, roles_path,
         stereo, bgm, llm_url, tts_url, voice, engine_priority):
    """
    统一编排入口

    Args:
        engine_priority: "auto" | "minimax" | "qwen"
    """
    total_start = time.time()
    engs = check_engines()

    console.print(Panel.fit(
        f"[bold cyan]AI Content Studio Orchestrator[/bold cyan]\n"
        f"模式: {mode}  |  优先引擎: {engine_priority}\n"
        f"源: {source[:40]}{'...' if len(source) > 40 else ''}",
        title="Studio Orchestrator"
    ))

    llm_time = tts_time = 0.0
    used_engine = None

    # ── Qwen Omni only ──
    if engine_priority == "qwen":
        if not engs["qwen_omni_studio"]:
            console.print("[red]✗ Qwen Omni 未配置 API Key[/red]")
            return False, None, 0
        start = time.time()
        ok = run_qwen_studio(source, mode, output, instruction, voice)
        used_engine = "qwen_omni"
        tts_time = time.time() - start
        total_time = time.time() - total_start
        return ok, used_engine, total_time

    # ── MiniMax only ──
    if engine_priority == "minimax":
        if not engs["minimax_studio"]:
            console.print("[red]✗ MiniMax 未配置 API Key[/red]")
            return False, None, 0
        try:
            llm_start = time.time()
            ok = run_minimax_studio(source, mode, output, instruction,
                                    roles_path, stereo, bgm, llm_url, tts_url)
            used_engine = "minimax"
            total_time = time.time() - total_start
            return ok, used_engine, total_time
        except RuntimeError as e:
            console.print(f"[red]✗ MiniMax 流程失败: {e}[/red]")
            return False, None, 0

    # ── Auto: MiniMax 优先，失败 fallback Qwen ──
    if engine_priority == "auto":
        # 尝试 MiniMax
        if engs["minimax_studio"]:
            try:
                llm_start = time.time()
                ok = run_minimax_studio(source, mode, output, instruction,
                                        roles_path, stereo, bgm, llm_url, tts_url)
                used_engine = "minimax"
                total_time = time.time() - total_start
                return ok, used_engine, total_time
            except RuntimeError as e:
                console.print(f"[yellow]⚠ MiniMax 流程失败: {e}[/yellow]")

        # Fallback to Qwen Omni
        if engs["qwen_omni_studio"]:
            console.print(f"[yellow]→ Fallback: 切换到 Qwen Omni...[/yellow]")
            start = time.time()
            ok = run_qwen_studio(source, mode, output, instruction, voice)
            used_engine = "qwen_omni"
            tts_time = time.time() - start
            total_time = time.time() - total_start
            return ok, used_engine, total_time
        else:
            console.print("[red]✗ 所有引擎均不可用[/red]")
            return False, None, 0

    return False, None, 0


def print_summary(source, mode, output, engine, total_time):
    """打印执行摘要"""
    engine_label = {
        "minimax": "MiniMax Content Studio",
        "qwen_omni": "Qwen Omni Studio (Fallback)",
    }.get(engine, engine)

    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("引擎", engine_label or "—")
    table.add_row("模式", mode)
    table.add_row("输出", str(output))
    table.add_row("总耗时", f"{total_time:.2f}s")

    console.print(Panel.fit(table, title="[bold green]✓ 执行完成[/bold green]", border_style="green"))


# ──────────────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AI Content Studio Orchestrator — MiniMax 优先 / Qwen Omni Fallback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
引擎优先级（--engine）:
  auto     MiniMax 优先，失败自动切换到 Qwen Omni（全流程 fallback，默认）
  minimax  仅使用 MiniMax Content Studio
  qwen     仅使用 Qwen Omni Studio

模式（--mode）:
  deep_dive  深入探究，广播级播客对话
  summary    摘要，专业简报
  review     评论，建设性批评
  debate     辩论，正反方对辩

示例:
  python studio_orchestrator.py --source "源文本" --mode summary -o out.mp3
  python studio_orchestrator.py --source "源文本" --engine qwen -o out.mp3
  python studio_orchestrator.py --check
"""
    )
    parser.add_argument("--source", help="源文本内容或文件路径（--check 时可选）")
    parser.add_argument("--mode", default="deep_dive",
                        choices=["deep_dive", "summary", "review", "debate"],
                        help="生成模式")
    parser.add_argument("-o", "--output", default=None,
                        help="输出文件路径（默认: outputs/auto_<timestamp>.mp3）")
    parser.add_argument("--instruction", help="额外要求")
    parser.add_argument("-r", "--roles",
                        default=str(DIR / "configs" / "studio_roles.json"),
                        help="角色库配置文件")
    parser.add_argument("--stereo", action="store_true", help="开启立体声")
    parser.add_argument("--bgm", help="背景音乐文件")
    parser.add_argument("--llm-url", help="MiniMax LLM API URL")
    parser.add_argument("--tts-url", help="MiniMax TTS API URL")
    parser.add_argument("-v", "--voice", default="cherry", help="音色（Qwen Omni）")
    parser.add_argument("--engine", default="auto",
                        choices=["auto", "minimax", "qwen"],
                        help="引擎优先级")
    parser.add_argument("--check", action="store_true", help="仅检查引擎可用性")

    args = parser.parse_args()

    # 检查引擎状态
    if args.check:
        print_engine_status()
        sys.exit(0)

    # 校验参数
    if not args.source:
        parser.print_help()
        console.print("\n[yellow]提示: 使用 --check 检查引擎状态[/yellow]")
        sys.exit(1)

    if not args.output:
        import time as _time
        ts = int(_time.time())
        args.output = str(OUTPUTS_DIR / f"auto_{ts}.mp3")

    # 角色库路径发现
    roles_path = Path(args.roles)
    if not roles_path.exists():
        fallback = DIR / "roles.json"
        if fallback.exists():
            roles_path = fallback

    # 执行编排
    ok, engine, total = run(
        source=args.source,
        mode=args.mode,
        output=args.output,
        instruction=args.instruction,
        roles_path=str(roles_path),
        stereo=args.stereo,
        bgm=args.bgm,
        llm_url=args.llm_url,
        tts_url=args.tts_url,
        voice=args.voice,
        engine_priority=args.engine,
    )

    if ok:
        print_summary(args.source, args.mode, args.output, engine, total)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
