"""
MiniMax AI Content Studio - LLM 脚本生成引擎 (V5.1)
直接调用 MiniMax API，绕过中间层
"""
import os
import json
import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from cachetools import TTLCache

import requests

console = Console()

# Constants
CONFIG_PATH = Path.home() / ".config" / "opencode" / "opencode.json"

# LLM 响应缓存（内存,5分钟 TTL)
llm_cache = TTLCache(maxsize=100, ttl=300)

MODES = {
    "deep_dive": {
        "name": "深入探究 (V5 Studio Pro)",
        "description": "广播级深度对谈,具备'认知冲突'叙事弧与'自我修正'机制",
        "system": """你是一位获得过皮博迪奖（Peabody Award）的顶尖播客制作人,擅长策划极具穿透力的深度对谈。
你的任务是将枯燥的素材转化为一段充满戏剧冲突、逻辑拆解与思维火花的 100% 仿真播客。

叙事弧 (Narrative Arc) 设计:
1. 开篇：Alex 表现出极大的兴趣,但 Sam 表现出适度的怀疑或认为某个观点"太超前/不合理"。
2. 摩擦：Alex 试图说服 Sam,两人针对核心难点进行思维拉锯,甚至会有"Wait, but this source says..."的挑战。
3. 突破：Sam 突然通过一个天才级的比喻 宄现逻辑闭环,两人均表现出"OMG, I get it now!"的兴奋感。
4. 总结:并非简单的复述,而是提炼出对现实生活的深远意义。

高级拟人技巧:
- 自我修正：允许主持人说错话后立即纠正。例如:"实际上……哦,等下,我刚才看错了,应该是……"
- 交互重叠标记:使用 [Alex, interject]: (right) 或 来表示在对方说话时的微小反馈。
- 动态语速：在兴奋点加快语速,在深思点放慢,并使用 `<#0.5#>` 这种停顿标记。
- 语气词进化：, (well), (literally), (I mean) 的自然穿插。

注意:只输出脚本正文,不要有任何额外说明。"""
    },
    "summary": {
        "name": "摘要",
        "description": "简短概要,旨在帮助您快速了解来源的核心思想",
        "system": """你是一位资讯简报员。你的任务是将提供的来源文字转换成一段专业、干练的单人摘要播报脚本。
角色:解说员

遵循以下格式:
[Narrator, neutral]: <播报内容>

要求:
1. 核心观点明确。
2. 语言精炼。
3. 输出纯文本脚本。"""
    },
    "review": {
        "name": "评论",
        "description": "对来源的专家评价,旨在提供建设性反馈,帮助您改进内容",
        "system": """你是一位资深的行业评论家。你的任务是将提供的来源文字给出批判性的、建设性的专家评价脚本。
角色:专家

遵循以下格式:
[Expert, calm]: <评价内容>
[Expert, neutral]: <后续建议>

要求:
1. 态度中肯且专业。
2. 包含优点与不足,并给出改进方向。
3. 输出纯文本脚本。"""
    },
    "debate": {
        "name": "辩论",
        "description": "两位主持人之间思维缜密的辩论,旨在阐明对来源的不同观点",
        "system": """你是一位辩论赛主席。你的任务是将提供的来源文字转换成一段思维缜密的双人辩论脚本。
辩手 A (Proponent): 捍卫来源中的核心观点。
辩手 B (Opponent): 提出合理的质疑和反面视角。

遵循以下格式:
[Proponent, neutral]: <陈述/反驳内容>
[Opponent, neutral]: <挑战/质疑内容>

要求:
1. 逻辑博弈感强。
2. 双方立场鲜明。
3. 输出纯文本脚本。"""
    }
}


def load_config():
    """加载 opencode.json 配置"""
    if not CONFIG_PATH.exists():
        console.print(f"[red]配置文件不存在: {CONFIG_PATH}[/red]")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def get_minimax_config():
    """从配置文件获取 MiniMax 配置"""
    config = load_config()
    providers = config.get("provider", {})
    minimax_config = providers.get("minimax", {})

    if not minimax_config:
        raise ValueError("MiniMax provider not found in config")

    options = minimax_config.get("options", {})
    api_key = options.get("apiKey")
    base_url = options.get("baseURL", "https://api.minimax.io/anthropic/v1")

    return {
        "api_key": api_key,
        "base_url": base_url,
        "models": minimax_config.get("models", {})
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=lambda retry_state: console.print(
        f"[yellow]重试中... (尝试 {retry_state.attempt_number}/3)[/yellow]"
    )
)
def call_minimax_api(messages, model="MiniMax-M2.7", temperature=0.7, max_tokens=4096):
    """直接调用 MiniMax API（支持 Anthropic 格式）"""
    config = get_minimax_config()

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }

    # 使用 Anthropic 格式的 API 端点
    api_url = f"{config['base_url']}/v1/messages"

    # 转换 messages 格式为 Anthropic 格式
    anthropic_messages = []
    system_prompt = None
    for msg in messages:
        if msg['role'] == 'system':
            system_prompt = msg['content']
        else:
            anthropic_messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": anthropic_messages
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()

        result = response.json()

        # Anthropic 格式响应
        if "content" in result:
            # content 是列表格式 [{"type": "thinking", ...}, {"type": "text", "text": "..."}]
            content_list = result["content"]
            if isinstance(content_list, list):
                # 找到 type="text" 的块
                for block in content_list:
                    if block.get("type") == "text":
                        return block.get("text", "")
                # 如果没有 text 块,返回空字符串
                console.print(f"[yellow]⚠ 响应中没有 text 块[/yellow]")
                return ""
            else:
                return str(content_list)
        elif "choices" in result:
            # OpenAI 格式响应（兼容）
            return result["choices"][0]["message"]["content"]
        else:
            console.print(f"[red]API 响应格式错误: {result}[/red]")
            raise ValueError("Invalid response format")

    except Exception as e:
        console.print(f"[red]API call failed: {e}[/red]")
        raise


def generate_script_with_cache(source_text: str, mode: str, instruction: str = None) -> str:
    """带缓存的脚本生成"""
    # 构建缓存键
    cache_key = f"{mode}:{hash(source_text)}:{hash(instruction or '')}"

    if cache_key in llm_cache:
        console.print("[green]✓ 命中 LLM 缓存,跳过调用[/green]")
        return llm_cache[cache_key]

    if mode not in MODES:
        raise ValueError(f"Invalid mode: {mode}")

    mode_config = MODES[mode]
    system_prompt = mode_config["system"]

    user_prompt = f"来源文字:\n{source_text}\n\n"
    if instruction:
        user_prompt += f"特别要求:{instruction}\n\n"
    user_prompt += "请生成脚本:"

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]生成脚本中...", total=None)

        try:
            # 直接调用 MiniMax API
            content = call_minimax_api(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="MiniMax-M2.7"
            )

            # 存入缓存
            llm_cache[cache_key] = content

            progress.update(task, description=f"[green]✓ 脚本生成完成 ({len(content)} 字符)[/green]")
            return content

        except Exception as e:
            progress.update(task, description=f"[red]✗ 生成失败: {e}[/red]")
            raise


def main():
    parser = argparse.ArgumentParser(description="MiniMax AI Content Studio - LLM 脚本引擎 (V5.1)")
    parser.add_argument("--source", required=True, help="来源文字或文本文件路径")
    parser.add_argument("--mode", choices=list(MODES.keys()), default="deep_dive", help="生成模式")
    parser.add_argument("--instruction", help="额外的自然语言要求")
    parser.add_argument("--output", default="content_script.txt", help="脚本保存路径")

    args = parser.parse_args()

    # 读取源内容
    source_path = Path(args.source)
    if source_path.exists():
        source_content = source_path.read_text(encoding="utf-8")
    else:
        source_content = args.source

    console.print(Panel.fit(
        f"[bold cyan]MiniMax Content Studio V5.1[/bold cyan]\n"
        f"模式: {MODES[args.mode]['name']}\n"
        f"源长度: {len(source_content)} 字符",
        title="LLM 脚本引擎"
    ))

    try:
        script = generate_script_with_cache(source_content, args.mode, args.instruction)

        if script:
            output_path = Path(args.output)
            output_path.write_text(script, encoding="utf-8")
            console.print(f"\n[green]✓ 脚本已保存至: {output_path}[/green]")
        else:
            console.print("[red]✗ 脚本生成失败[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗ 发生错误: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
