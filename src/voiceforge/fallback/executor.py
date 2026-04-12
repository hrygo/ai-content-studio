"""通用 Fallback 执行器"""
import logging
from typing import Callable, TypeVar

from voiceforge.entities.errors import ErrorType

logger = logging.getLogger(__name__)

T = TypeVar("T")

# TTS 引擎 fallback 映射
_TTS_FALLBACK = {
    "minimax": "qwen_tts",
    "qwen_tts": "minimax",
    "qwen_omni": "minimax",
    "qwen": "minimax",
}

# LLM 引擎 fallback 映射
_LLM_FALLBACK = {
    "minimax": "qwen",
    "qwen": "minimax",
}


def get_fallback_engine(engine_name: str) -> str | None:
    return _TTS_FALLBACK.get(engine_name)


def get_fallback_llm_engine(engine_name: str) -> str | None:
    return _LLM_FALLBACK.get(engine_name)


class FallbackExecutor:
    """通用 fallback 执行器

    主函数失败时自动切换到备用函数，
    基于错误类型判断是否 fallback，防无限循环。
    """

    def __init__(
        self,
        primary: Callable[..., T],
        fallback: Callable[..., T] | None = None,
        should_fallback: Callable[[str | None], bool] | None = None,
    ):
        self.primary = primary
        self.fallback = fallback
        self._should_fallback = should_fallback or self._default_should_fallback
        self._fallback_attempted = False

    def execute(self, *args, **kwargs) -> T:
        try:
            result = self.primary(*args, **kwargs)
            if self._is_success(result):
                return result
            error_msg = self._get_error(result)
            if self._should_fallback(error_msg):
                return self._try_fallback(*args, **kwargs)
            return result
        except Exception as e:
            logger.warning(f"主函数异常: {e}")
            return self._try_fallback(*args, **kwargs)

    def _try_fallback(self, *args, **kwargs) -> T:
        if not self.fallback:
            return self.primary(*args, **kwargs)
        if self._fallback_attempted:
            return self.primary(*args, **kwargs)
        self._fallback_attempted = True
        logger.info("切换 fallback...")
        try:
            return self.fallback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback 异常: {e}")
            return self.primary(*args, **kwargs)

    @staticmethod
    def _is_success(result) -> bool:
        return getattr(result, "success", False)

    @staticmethod
    def _get_error(result) -> str | None:
        return getattr(result, "error_message", None)

    @staticmethod
    def _default_should_fallback(error_message: str | None) -> bool:
        return ErrorType.classify(error_message) == ErrorType.FALLBACK
