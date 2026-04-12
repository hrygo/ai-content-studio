"""Qwen/DashScope API 客户端"""
import logging
import os
from typing import Iterator

from .base import BaseAPIClient, APIResponseError

logger = logging.getLogger(__name__)


class QwenClient(BaseAPIClient):
    """Qwen API 客户端（通义千问 / DashScope）"""

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        api_key = api_key or os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        base_url = base_url or os.getenv("QWEN_BASE_URL") or self.DEFAULT_BASE_URL
        super().__init__(api_key, base_url)

    # -- LLM（非流式）--
    def generate_text(
        self, prompt: str, model: str = "qwen3.5-flash",
        temperature: float = 0.7, max_tokens: int = 2000,
    ) -> str | None:
        """Qwen 文本生成"""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens,
        }
        try:
            resp = self.request("POST", url, json=payload)
            result = resp.json()
            choices = result.get("choices", [])
            return choices[0].get("message", {}).get("content") if choices else None
        except Exception as e:
            logger.error(f"Qwen 文本生成失败: {e}")
            return None

    # -- LLM（流式）--
    def generate_text_stream(
        self, prompt: str, model: str = "qwen3.5-flash",
        temperature: float = 0.7, max_tokens: int = 2000,
    ) -> Iterator[str]:
        """Qwen 流式文本生成"""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens, "stream": True,
        }
        try:
            resp = self.session.post(
                url, headers=self._headers(), json=payload, stream=True, timeout=60,
            )
            yield from self._parse_sse_stream(resp)
        except Exception as e:
            logger.error(f"Qwen 流式生成失败: {e}")
            raise

    # -- TTS（Qwen 专用 API）--
    def text_to_speech(
        self, text: str, voice: str = "cherry",
        model: str = "qwen3-tts-flash", language: str = "Auto",
    ) -> bytes | None:
        """Qwen TTS API（原生 DashScope 端点，返回 WAV 字节）"""
        # 原生端点（非 OpenAI 兼容）
        api_endpoint = self.base_url.replace("/compatible-mode/v1", "").rstrip("/")
        url = f"{api_endpoint}/api/v1/services/aigc/multimodal-generation/generation"

        payload = {
            "model": model,
            "input": {"text": text, "voice": voice.lower(), "language_type": language},
        }
        try:
            resp = self.request("POST", url, json=payload)
            result = resp.json()
            audio_url = result.get("output", {}).get("audio", {}).get("url")
            if not audio_url:
                logger.error(f"响应中无音频 URL: {result}")
                return None

            audio_resp = self.session.get(audio_url, timeout=60)
            audio_resp.raise_for_status()
            return audio_resp.content
        except Exception as e:
            logger.error(f"Qwen TTS 失败: {e}")
            return None
