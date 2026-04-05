"""
Fallback 执行器

通用的 fallback 机制，支持主引擎失败时自动切换到备用引擎
"""
from typing import Optional, Callable, TypeVar, Protocol
import logging

from ..entities.errors import ErrorType

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FallbackExecutor:
    """通用的 fallback 执行器

    支持主函数失败时自动切换到备用函数
    基于错误类型智能判断是否应该 fallback
    防止无限循环（只尝试一次 fallback）

    Example:
        >>> executor = FallbackExecutor(
        ...     primary=lambda: engine1.synthesize(),
        ...     fallback=lambda: engine2.synthesize()
        ... )
        >>> result = executor.execute()
    """

    def __init__(
        self,
        primary: Callable[..., T],
        fallback: Optional[Callable[..., T]] = None,
        should_fallback_func: Optional[Callable[[str | None], bool]] = None,
    ):
        """
        初始化 Fallback 执行器

        Args:
            primary: 主函数
            fallback: 备用函数（可选）
            should_fallback_func: 判断是否应该 fallback 的函数（可选）
        """
        self.primary = primary
        self.fallback = fallback
        self.should_fallback_func = should_fallback_func or self._default_should_fallback
        self._fallback_attempted = False

    def execute(self, *args, **kwargs) -> T:
        """
        执行主函数，失败时尝试 fallback

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            T: 执行结果
        """
        try:
            result = self.primary(*args, **kwargs)

            # 检查结果是否成功
            if self._is_success(result):
                return result

            # 结果失败，检查是否应该 fallback
            error_message = self._get_error_message(result)
            if self.should_fallback_func(error_message):
                return self._try_fallback(*args, **kwargs)

            return result

        except Exception as e:
            logger.warning(f"主函数执行异常: {e}")
            return self._try_fallback(*args, **kwargs)

    def _try_fallback(self, *args, **kwargs) -> T:
        """尝试执行 fallback 函数"""
        if not self.fallback:
            logger.warning("没有配置 fallback 函数")
            # 返回主函数的结果（即使失败）
            return self.primary(*args, **kwargs)

        if self._fallback_attempted:
            logger.warning("已经尝试过 fallback，避免无限循环")
            return self.primary(*args, **kwargs)

        logger.info("切换到 fallback 函数...")
        self._fallback_attempted = True

        try:
            return self.fallback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback 函数执行异常: {e}")
            # 返回主函数的结果（即使失败）
            return self.primary(*args, **kwargs)

    @staticmethod
    def _is_success(result) -> bool:
        """判断结果是否成功"""
        return getattr(result, "success", False)

    @staticmethod
    def _get_error_message(result) -> str | None:
        """获取结果中的错误消息"""
        return getattr(result, "error_message", None)

    @staticmethod
    def _default_should_fallback(error_message: str | None) -> bool:
        """默认的 fallback 判断逻辑"""
        error_type = ErrorType.classify(error_message)
        return error_type == ErrorType.FALLBACK


def get_fallback_engine(engine_name: str) -> Optional[str]:
    """
    获取 TTS 引擎的 fallback 对应引擎

    Args:
        engine_name: 引擎名称

    Returns:
        Optional[str]: Fallback 引擎名称，如果没有则返回 None
    """
    fallback_map = {
        "minimax": "qwen_tts",
        "qwen_tts": "minimax",
        "qwen_omni": "minimax",
        "qwen": "minimax",
    }
    return fallback_map.get(engine_name)


def get_fallback_llm_engine(engine_name: str) -> Optional[str]:
    """
    获取 LLM 引擎的 fallback 对应引擎

    Args:
        engine_name: 引擎名称

    Returns:
        Optional[str]: Fallback LLM 引擎名称，如果没有则返回 None
    """
    fallback_map = {
        "minimax": "qwen",
        "MiniMaxLLMEngine": "QwenLLMEngine",
        "qwen": "minimax",
        "QwenLLMEngine": "MiniMaxLLMEngine",
    }
    return fallback_map.get(engine_name)
