"""
TTS 引擎基类
定义统一的 TTS 引擎接口
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseTTSEngine(ABC):
    """TTS 引擎基类"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.params = kwargs

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_file: str,
        voice: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        合成语音

        Args:
            text: 待合成文本
            output_file: 输出文件路径
            voice: 音色 ID
            **kwargs: 其他 TTS 参数

        Returns:
            成功返回 True，失败返回 False
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass

    @abstractmethod
    def get_supported_voices(self) -> list:
        """获取支持的音色列表"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        return {
            "name": self.__class__.__name__,
            "api_key": "***" if self.api_key else None,
            "base_url": self.base_url,
            "available": self.is_available(),
            "voices_count": len(self.get_supported_voices())
        }
