"""
用例层（Use Cases）- 业务逻辑规则

整洁架构第二层，定义业务用例和规则。

特点：
- 封装业务逻辑
- 协调实体交互
- 调用基础设施层（通过接口）
- 独立于框架和外部服务
"""

from .tts_use_cases import (
    SynthesizeSpeechUseCase,
    BatchSynthesizeUseCase,
)

__all__ = [
    "SynthesizeSpeechUseCase",
    "BatchSynthesizeUseCase",
]
