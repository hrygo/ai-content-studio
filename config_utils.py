"""
config_utils.py — AI Content Studio 统一配置加载
所有引擎共享：opencode.json 读取、API Key/URL 解析
"""
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 配置路径 ─────────────────────────────────────────────────

def get_config_path():
    """固定指向 ~/.config/opencode/opencode.json 配置文件"""
    return os.path.expanduser("~/.config/opencode/opencode.json")


# ── 统一配置加载器 ─────────────────────────────────────────────

def load_opencode_config(provider="bailian", api_url_default=None):
    """
    从 opencode.json 加载 API Key 和 URL，按 provider 分发。

    Args:
        provider: "bailian" (Qwen) | "minimax"
        api_url_default: 可选的 URL 默认值（仅 provider="bailian" 使用）

    Returns:
        (api_key: str | None, api_url: str)
        - bailian: (key, url) 两者均可为 None
        - minimax: (key, None)  — minimax 不从配置读 URL
    """
    config_path = get_config_path()

    if not os.path.exists(config_path):
        return None, None

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return None, None

    if provider == "bailian":
        bailian = config.get("provider", {}).get("bailian", {}).get("options", {})
        api_key = os.environ.get("DASHSCOPE_API_KEY") or bailian.get("apiKey")
        api_url = os.environ.get("DASHSCOPE_BASE_URL") or bailian.get("baseURL") or api_url_default
        return api_key, (api_url.rstrip("/") if api_url else None)

    elif provider == "minimax":
        minimax = config.get("provider", {}).get("minimax", {}).get("options", {})
        api_key = os.environ.get("MINIMAX_TTS_API_KEY") or os.environ.get("MINIMAX_API_KEY") \
                  or minimax.get("apiKey")
        return api_key, None

    return None, None


# ── 各引擎兼容包装 ────────────────────────────────────────────

def load_api_key():
    """MiniMax API Key（向后兼容包装）"""
    key, _ = load_opencode_config(provider="minimax")
    return key


def load_api_config():
    """
    DashScope / Bailian API 配置（向后兼容包装）
    qwen3-omni-flash 使用 /compatible-mode/v1 端点
    """
    return load_opencode_config(
        provider="bailian",
        api_url_default="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


def load_qwen_tts_config():
    """
    qwen3-tts-flash API 配置（向后兼容包装）
    qwen3-tts-flash 使用独立端点（非 /compatible-mode/v1）
    """
    return load_opencode_config(
        provider="bailian",
        api_url_default="https://dashscope.aliyuncs.com"
    )
