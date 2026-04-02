"""
配置管理器 - API Key 加载

加载顺序（优先级从高到低）：
1. 环境变量：MINIMAX_API_KEY, MINIMAX_GROUP_ID, DASHSCOPE_API_KEY, QWEN_API_KEY
2. ~/.config/opencode/opencode.json（向后兼容）

opencode.json 结构：
{
  "provider": {
    "minimax": {
      "options": {
        "apiKey": "...",
        "groupId": "..."
      }
    },
    "bailian": {
      "options": {
        "apiKey": "...",
        "baseURL": "..."
      }
    }
  }
}
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_OPENCODE_CONFIG_PATH = Path.home() / ".config" / "opencode" / "opencode.json"


def _load_opencode_json() -> dict:
    """从 opencode.json 加载配置（如果存在）"""
    if not _OPENCODE_CONFIG_PATH.exists():
        return {}
    try:
        with open(_OPENCODE_CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"无法读取 opencode.json: {e}")
        return {}


class ConfigManager:
    """
    API Key 配置管理器

    统一加载 API Key，支持环境变量和 opencode.json。
    """

    def __init__(self):
        self._opencode = _load_opencode_json()

    # ── MiniMax ──────────────────────────────────────────────

    def get_minimax_api_key(self) -> Optional[str]:
        """获取 MiniMax API Key"""
        # 环境变量优先
        key = os.getenv("MINIMAX_API_KEY") or os.getenv("MINIMAX_TTS_API_KEY")
        if key:
            return key
        # opencode.json fallback
        try:
            return self._opencode.get("provider", {}).get("minimax", {}).get("options", {}).get("apiKey")
        except Exception:
            return None

    def get_minimax_group_id(self) -> Optional[str]:
        """获取 MiniMax Group ID"""
        gid = os.getenv("MINIMAX_GROUP_ID")
        if gid:
            return gid
        try:
            return self._opencode.get("provider", {}).get("minimax", {}).get("options", {}).get("groupId")
        except Exception:
            return None

    # ── Qwen / DashScope ─────────────────────────────────────

    def get_qwen_api_key(self) -> Optional[str]:
        """获取 Qwen/DashScope API Key"""
        key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if key:
            return key
        try:
            return self._opencode.get("provider", {}).get("bailian", {}).get("options", {}).get("apiKey")
        except Exception:
            return None

    def get_qwen_base_url(self) -> Optional[str]:
        """获取 Qwen Base URL"""
        url = os.getenv("DASHSCOPE_BASE_URL")
        if url:
            return url
        try:
            return self._opencode.get("provider", {}).get("bailian", {}).get("options", {}).get("baseURL")
        except Exception:
            return None

    # ── 检查 ──────────────────────────────────────────────────

    def is_minimax_configured(self) -> bool:
        """MiniMax 是否已配置"""
        return bool(self.get_minimax_api_key() and self.get_minimax_group_id())

    def is_qwen_configured(self) -> bool:
        """Qwen 是否已配置"""
        return bool(self.get_qwen_api_key())


# 全局实例（延迟初始化）
_config: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器全局实例"""
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config
