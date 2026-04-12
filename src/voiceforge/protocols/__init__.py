"""Protocol 接口定义"""

from .engine import TTSEngine, LLMEngine
from .processor import AudioProcessor

__all__ = ["TTSEngine", "LLMEngine", "AudioProcessor"]
