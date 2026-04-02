"""
配置管理系统
统一管理 API Key、引擎参数、路径配置
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """引擎配置"""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    voice: Optional[str] = None
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径（JSON 格式），优先级低于环境变量
        """
        self.config_file = config_file
        self.config_data: Dict[str, Any] = {}
        self.engines: Dict[str, EngineConfig] = {}

        # 加载配置
        self._load_from_file()
        self._load_from_env()
        self._init_engines()

    def _load_from_file(self):
        """从配置文件加载"""
        if not self.config_file:
            return

        config_path = Path(self.config_file)
        if not config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_file}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
            logger.info(f"已加载配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config_data = {}

    def _load_from_env(self):
        """从环境变量加载（优先级最高）"""
        # MiniMax 配置
        if "MINIMAX_API_KEY" in os.environ:
            self.config_data.setdefault("minimax", {})["api_key"] = os.environ["MINIMAX_API_KEY"]
        if "MINIMAX_BASE_URL" in os.environ:
            self.config_data.setdefault("minimax", {})["base_url"] = os.environ["MINIMAX_BASE_URL"]
        if "MINIMAX_API_URL" in os.environ:
            self.config_data.setdefault("minimax", {})["base_url"] = os.environ["MINIMAX_API_URL"]
        if "MINIMAX_LLM_API_URL" in os.environ:
            self.config_data.setdefault("minimax_llm", {})["base_url"] = os.environ["MINIMAX_LLM_API_URL"]
        if "MINIMAX_TTS_API_URL" in os.environ:
            self.config_data.setdefault("minimax_tts", {})["base_url"] = os.environ["MINIMAX_TTS_API_URL"]

        # Qwen 配置
        if "QWEN_API_KEY" in os.environ:
            self.config_data.setdefault("qwen", {})["api_key"] = os.environ["QWEN_API_KEY"]
        if "DASHSCOPE_API_KEY" in os.environ:
            self.config_data.setdefault("qwen", {})["api_key"] = os.environ["DASHSCOPE_API_KEY"]
        if "QWEN_BASE_URL" in os.environ:
            self.config_data.setdefault("qwen", {})["base_url"] = os.environ["QWEN_BASE_URL"]

    def _init_engines(self):
        """初始化引擎配置"""
        # MiniMax 引擎
        minimax_cfg = self.config_data.get("minimax", {})
        self.engines["minimax"] = EngineConfig(
            name="minimax",
            api_key=minimax_cfg.get("api_key"),
            base_url=minimax_cfg.get("base_url"),
            model=minimax_cfg.get("model", "M2-preview-1004"),
            voice=minimax_cfg.get("voice", "male-qn-qingse"),
            enabled=bool(minimax_cfg.get("api_key")),
            params=minimax_cfg.get("params", {})
        )

        # Qwen 引擎
        qwen_cfg = self.config_data.get("qwen", {})
        self.engines["qwen"] = EngineConfig(
            name="qwen",
            api_key=qwen_cfg.get("api_key"),
            base_url=qwen_cfg.get("base_url"),
            model=qwen_cfg.get("model", "qwen-turbo"),
            voice=qwen_cfg.get("voice", "cherry"),
            enabled=bool(qwen_cfg.get("api_key")),
            params=qwen_cfg.get("params", {})
        )

    def get_engine_config(self, engine_name: str) -> Optional[EngineConfig]:
        """获取引擎配置"""
        return self.engines.get(engine_name)

    def get_api_key(self, engine_name: str) -> Optional[str]:
        """获取指定引擎的 API Key"""
        engine = self.get_engine_config(engine_name)
        return engine.api_key if engine else None

    def get_base_url(self, engine_name: str) -> Optional[str]:
        """获取指定引擎的 Base URL"""
        engine = self.get_engine_config(engine_name)
        return engine.base_url if engine else None

    def is_engine_enabled(self, engine_name: str) -> bool:
        """检查引擎是否启用"""
        engine = self.get_engine_config(engine_name)
        return engine.enabled if engine else False

    def get_all_engines(self) -> Dict[str, EngineConfig]:
        """获取所有引擎配置"""
        return self.engines.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（支持点号路径）"""
        keys = key.split(".")
        value = self.config_data

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置值（支持点号路径）"""
        keys = key.split(".")
        data = self.config_data

        for k in keys[:-1]:
            data = data.setdefault(k, {})

        data[keys[-1]] = value

    def save(self):
        """保存配置到文件"""
        if not self.config_file:
            logger.warning("未指定配置文件路径，无法保存")
            return

        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")


# 全局配置实例
_config_manager: Optional[ConfigManager] = None


def get_config(config_file: Optional[str] = None) -> ConfigManager:
    """获取全局配置实例"""
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager(config_file)

    return _config_manager


def init_config(config_file: Optional[str] = None) -> ConfigManager:
    """初始化全局配置"""
    global _config_manager
    _config_manager = ConfigManager(config_file)
    return _config_manager
