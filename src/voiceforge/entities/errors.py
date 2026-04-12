"""错误类型分类"""
from enum import Enum


class ErrorType(Enum):
    """错误类型 — 决定处理策略"""

    RETRYABLE = "retryable"   # 网络错误、临时故障 → 重试
    FALLBACK = "fallback"     # 余额不足、音色错误 → 切换引擎
    FATAL = "fatal"           # 配置错误、参数错误 → 直接失败

    @classmethod
    def classify(cls, error_message: str | None) -> "ErrorType":
        if not error_message:
            return cls.FATAL

        msg = error_message.lower()

        retryable_keywords = [
            "timeout", "connection", "network", "temporarily",
            "rate limit", "超时", "网络", "连接", "限流",
            "1001", "1013", "1021", "2056",
        ]
        if any(kw in msg for kw in retryable_keywords):
            return cls.RETRYABLE

        fallback_keywords = [
            "1008", "insufficient", "余额", "balance",
            "voice", "licensed", "not licensed", "invalid voice",
        ]
        if any(kw in msg for kw in fallback_keywords):
            return cls.FALLBACK

        if "api" in msg and any(kw in msg for kw in ["error", "失败", "错误", "bad request"]):
            return cls.FALLBACK

        return cls.FATAL
