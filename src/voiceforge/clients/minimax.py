"""MiniMax API 客户端"""
import binascii
import logging
import os
from typing import Iterator

import requests

from .base import BaseAPIClient, RateLimitError, APIResponseError

logger = logging.getLogger(__name__)

_RATE_LIMIT_CODES = {1001, 1013, 1021, 2056}


class MiniMaxClient(BaseAPIClient):
    """MiniMax API 客户端（TTS + LLM）"""

    DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        api_key = api_key or os.getenv("MINIMAX_API_KEY")
        base_url = base_url or os.getenv("MINIMAX_BASE_URL") or self.DEFAULT_BASE_URL
        super().__init__(api_key, base_url)

    # -- TTS --
    def text_to_speech(
        self,
        text: str,
        model: str = "speech-2.8-hd",
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: int = 0,
        emotion: str = "neutral",
        **kwargs,
    ) -> bytes | None:
        """MiniMax TTS API（返回 MP3 字节）"""
        url = f"{self.base_url}/t2a_v2"

        voice_setting: dict = {
            "voice_id": voice_id, "speed": float(speed),
            "vol": float(vol), "pitch": int(pitch), "emotion": emotion,
        }
        if kwargs.get("english_normalization"):
            voice_setting["english_normalization"] = True
        if kwargs.get("latex_read"):
            voice_setting["latex_read"] = True

        payload = {
            "model": model, "text": text, "stream": False,
            "voice_setting": voice_setting,
            "audio_setting": {"sample_rate": 32000, "format": "mp3", "channel": 1},
        }
        for key in ("language_boost", "pronunciation_dict", "voice_modify"):
            if key in kwargs:
                payload[key] = kwargs[key]

        try:
            resp = self.request("POST", url, json=payload)
            result = resp.json()
            base_resp = result.get("base_resp", {})
            status_code = base_resp.get("status_code")

            if status_code in _RATE_LIMIT_CODES:
                raise RateLimitError(f"Rate limited ({status_code}): {base_resp.get('status_msg')}")
            if status_code != 0:
                raise APIResponseError(f"API 错误 {status_code}: {base_resp.get('status_msg')}")

            audio_hex = result.get("data", {}).get("audio")
            if not audio_hex:
                raise APIResponseError("响应中无音频数据")
            return binascii.unhexlify(audio_hex)

        except (APIResponseError, RateLimitError):
            raise
        except Exception as e:
            logger.error(f"MiniMax TTS 失败: {e}")
            return None

    # -- LLM（非流式）--
    def generate_text(
        self, prompt: str, model: str = "M2-preview-1004",
        temperature: float = 0.7, max_tokens: int = 2000,
    ) -> str | None:
        """MiniMax 文本生成"""
        url = f"{self.base_url}/text/chatcompletion_v2"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens,
        }
        try:
            resp = self.request("POST", url, json=payload)
            result = resp.json()
            base_resp = result.get("base_resp", {})
            if base_resp.get("status_code") != 0:
                raise APIResponseError(f"API 错误: {base_resp.get('status_msg')}")
            choices = result.get("choices", [])
            return choices[0].get("message", {}).get("content") if choices else None
        except Exception as e:
            logger.error(f"MiniMax 文本生成失败: {e}")
            return None

    # -- LLM（流式）--
    def generate_text_stream(
        self, prompt: str, model: str = "M2-preview-1004",
        temperature: float = 0.7, max_tokens: int = 2000,
    ) -> Iterator[str]:
        """MiniMax 流式文本生成"""
        url = f"{self.base_url}/text/chatcompletion_v2"
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
            logger.error(f"MiniMax 流式生成失败: {e}")
            raise
