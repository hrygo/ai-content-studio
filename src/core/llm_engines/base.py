"""
LLM 引擎基类
定义统一的 LLM 引擎接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Iterator, Dict, Any


class BaseLLMEngine(ABC):
    """LLM 引擎基类"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.params = kwargs

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """
        生成文本（非流式）

        Args:
            prompt: 提示词
            **kwargs: 模型参数

        Returns:
            生成的文本，失败返回 None
        """
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """
        生成文本（流式）

        Args:
            prompt: 提示词
            **kwargs: 模型参数

        Yields:
            文本片段
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "name": self.__class__.__name__,
            "api_key": "***" if self.api_key else None,
            "base_url": self.base_url,
            "available": self.is_available()
        }
