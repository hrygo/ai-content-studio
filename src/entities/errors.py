"""
错误类型枚举

用于分类不同类型的错误，决定处理策略
"""
from enum import Enum


class ErrorType(Enum):
    """错误类型"""

    RETRYABLE = "retryable"  # 可重试（网络错误、临时故障）
    FALLBACK = "fallback"  # 应切换引擎（余额不足、音色错误）
    FATAL = "fatal"  # 致命错误（配置错误、参数错误）

    @classmethod
    def classify(cls, error_message: str | None) -> "ErrorType":
        """
        根据错误消息分类错误类型

        Args:
            error_message: 错误消息

        Returns:
            ErrorType: 错误类型
        """
        if not error_message:
            return cls.FATAL

        msg = error_message.lower()

        # 网络错误、临时故障 → 可重试
        if any(
            keyword in msg
            for keyword in [
                "timeout",
                "connection",
                "network",
                "temporarily",
                "rate limit",
                "超时",
                "网络",
                "连接",
                "限流",
            ]
        ):
            return cls.RETRYABLE

        # 余额不足、音色错误 → 应切换引擎
        if any(
            keyword in msg
            for keyword in [
                "1008",
                "insufficient",
                "余额",
                "balance",
                "voice",
                "licensed",
                "not licensed",
                "invalid voice",
            ]
        ):
            return cls.FALLBACK

        # API 错误（非网络问题）→ 尝试 fallback
        if "api" in msg and any(
            keyword in msg for keyword in ["error", "失败", "错误", "bad request"]
        ):
            return cls.FALLBACK

        # 其他错误 → 致命错误
        return cls.FATAL
