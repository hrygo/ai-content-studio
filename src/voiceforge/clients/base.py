"""API 客户端基类 — 统一重试、SSE 解析、资源管理"""
import json
import logging
import weakref
import atexit
from typing import Iterator

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

_active_clients: weakref.WeakSet["BaseAPIClient"] = weakref.WeakSet()


class APIError(Exception):
    """API 客户端错误基类"""


class RateLimitError(APIError):
    """速率限制错误"""


class APIResponseError(APIError):
    """API 响应错误"""


class BaseAPIClient:
    """API 客户端基类

    支持：
    - 上下文管理器
    - atexit 自动清理
    - tenacity 重试
    - SSE 流式解析
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self._closed = False
        self.stats = {"requests": 0, "errors": 0, "retries": 0}
        _active_clients.add(self)

    # -- 上下文管理 --
    def __enter__(self) -> "BaseAPIClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        if not self._closed and hasattr(self, "session"):
            try:
                self.session.close()
                self._closed = True
            except Exception as e:
                logger.warning(f"关闭 session 失败: {e}")

    # -- 请求 --
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        retry=retry_if_exception_type((RateLimitError, requests.exceptions.RequestException)),
        before_sleep=lambda s: logger.warning(
            f"重试 {s.attempt_number}/5，等待 {s.next_action.sleep:.1f}s..."
        ),
    )
    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """统一请求（自动重试速率限制和网络错误）"""
        self.stats["requests"] += 1
        try:
            resp = self.session.request(
                method, url,
                headers=self._headers(),
                timeout=kwargs.pop("timeout", 30),
                **kwargs,
            )
            if resp.status_code == 429:
                self.stats["retries"] += 1
                raise RateLimitError("Rate limited (429)")
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            self.stats["errors"] += 1
            logger.error(f"API 请求失败: {e}")
            raise

    # -- SSE 流式解析（共用） --
    def _parse_sse_stream(self, response: requests.Response) -> Iterator[str]:
        """解析 SSE 流式响应，逐段 yield 文本内容"""
        for line in response.iter_lines():
            if not line or not line.startswith(b"data:"):
                continue
            data = line.decode("utf-8")[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                if content:
                    yield content
            except (json.JSONDecodeError, IndexError, KeyError):
                continue


@atexit.register
def _cleanup_clients() -> None:
    for client in list(_active_clients):
        try:
            if not client._closed:
                client.close()
        except Exception:
            pass
