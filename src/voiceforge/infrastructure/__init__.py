"""Infrastructure — CLI、配置、依赖注入"""

from .cli import main
from .container import Container

__all__ = ["main", "Container"]
