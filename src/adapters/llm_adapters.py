"""
LLM 引擎适配器 - Clean Architecture Adapters Layer

将 src/core/llm_engines/ 中的引擎适配到统一接口，供 use cases 层使用。
"""
from abc import ABC, abstractmethod
from typing import Optional, Iterator, Dict, Any
import logging

from ..services.api_client import MiniMaxClient, QwenClient

logger = logging.getLogger(__name__)


class LLMEngineInterface(ABC):
    """LLM 引擎接口 - 供 use case 层使用"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """生成文本（非流式）"""
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """生成文本（流式）"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass


class BaseLLMEngine(ABC):
    """LLM 引擎基类"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.params = kwargs

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """生成文本（非流式）"""
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """生成文本（流式）"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.__class__.__name__,
            "api_key": "***" if self.api_key else None,
            "base_url": self.base_url,
            "available": self.is_available()
        }


class MiniMaxLLMEngine(BaseLLMEngine):
    """MiniMax LLM 引擎"""

    DEFAULT_MODEL = "MiniMax-M2.7-highspeed"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self.model = model or self.DEFAULT_MODEL
        self.client = MiniMaxClient(api_key, base_url)

    def generate(self, prompt: str, temperature: float = 0.7,
                 max_tokens: int = 2000, **kwargs) -> Optional[str]:
        return self.client.generate_text(
            prompt=prompt,
            model=kwargs.get("model", self.model),
            temperature=temperature,
            max_tokens=max_tokens
        )

    def generate_stream(self, prompt: str, temperature: float = 0.7,
                       max_tokens: int = 2000, **kwargs) -> Iterator[str]:
        return self.client.generate_text_stream(
            prompt=prompt,
            model=kwargs.get("model", self.model),
            temperature=temperature,
            max_tokens=max_tokens
        )

    def is_available(self) -> bool:
        return self.client.api_key is not None

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info["model"] = self.model
        return info


class QwenLLMEngine(BaseLLMEngine):
    """Qwen LLM 引擎"""

    DEFAULT_MODEL = "qwen3.5-flash"
    SUPPORTED_MODELS = ["qwen3.5-flash", "qwen3-omni-flash"]

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None, **kwargs):
        super().__init__(api_key, base_url, **kwargs)
        self.model = model or self.DEFAULT_MODEL
        self.client = QwenClient(api_key, base_url)

    def generate(self, prompt: str, temperature: float = 0.7,
                 max_tokens: int = 2000, **kwargs) -> Optional[str]:
        return self.client.generate_text(
            prompt=prompt,
            model=kwargs.get("model", self.model),
            temperature=temperature,
            max_tokens=max_tokens
        )

    def generate_stream(self, prompt: str, temperature: float = 0.7,
                       max_tokens: int = 2000, **kwargs) -> Iterator[str]:
        return self.client.generate_text_stream(
            prompt=prompt,
            model=kwargs.get("model", self.model),
            temperature=temperature,
            max_tokens=max_tokens
        )

    def is_available(self) -> bool:
        return self.client.api_key is not None

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info["model"] = self.model
        info["supported_models"] = self.SUPPORTED_MODELS
        return info
