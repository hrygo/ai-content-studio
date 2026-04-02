"""
基础设施层（Infrastructure）- 框架和驱动

整洁架构最外层，处理外部世界交互。

特点：
- 框架和驱动（CLI、Web）
- 外部服务集成
- 配置和依赖注入
- 可替换框架而不影响内层
"""

from .cli import main
from .container import Container

__all__ = [
    "main",
    "Container",
]
