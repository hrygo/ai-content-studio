"""
Qwen LLM 引擎实现
支持通义千问系列模型
"""
from typing import Optional, Iterator, Dict, Any
import logging

from .base import BaseLLMEngine
from src.services.api_client import QwenClient

logger = logging.getLogger(__name__)


class QwenLLMEngine(BaseLLMEngine):
    """Qwen LLM 引擎"""

    DEFAULT_MODEL = "qwen3.5-flash"

    # 支持的模型列表
    SUPPORTED_MODELS = [
        "qwen3.5-flash",
        "qwen3-omni-flash"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ):
        super().__init__(api_key, base_url, **kwargs)
        self.model = model or self.DEFAULT_MODEL
        self.client = QwenClient(api_key, base_url)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """生成文本（非流式）"""
        return self.client.generate_text(
            prompt=prompt,
            model=kwargs.get("model", self.model),
            temperature=temperature,
            max_tokens=max_tokens
        )

    def generate_stream(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Iterator[str]:
        """生成文本（流式）"""
        return self.client.generate_text_stream(
            prompt=prompt,
            model=kwargs.get("model", self.model),
            temperature=temperature,
            max_tokens=max_tokens
        )

    def is_available(self) -> bool:
        """检查引擎是否可用"""
        return self.client.api_key is not None

    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        info = super().get_info()
        info["model"] = self.model
        info["supported_models"] = self.SUPPORTED_MODELS
        return info
