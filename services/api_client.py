"""
统一 API 客户端封装
提供 MiniMax / Qwen API 的统一调用接口，包含错误处理和重试机制
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any, Iterator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """API 客户端错误基类"""
    pass


class RateLimitError(APIClientError):
    """速率限制错误"""
    pass


class APIResponseError(APIClientError):
    """API 响应错误"""
    pass


class BaseAPIClient:
    """API 客户端基类"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.stats = {
            "requests": 0,
            "errors": 0,
            "retries": 0
        }

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, requests.exceptions.RequestException)),
        before_sleep=lambda retry_state: logger.warning(f"重试 {retry_state.attempt_number}/3...")
    )
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """统一请求方法，带重试机制"""
        self.stats["requests"] += 1

        try:
            response = self.session.request(
                method, url,
                headers=self._get_headers(),
                timeout=kwargs.pop("timeout", 30),
                **kwargs
            )

            # 速率限制
            if response.status_code == 429:
                self.stats["retries"] += 1
                raise RateLimitError("Rate limited (429)")

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            self.stats["errors"] += 1
            logger.error(f"API 请求失败: {e}")
            raise

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()


class MiniMaxClient(BaseAPIClient):
    """MiniMax API 客户端"""

    DEFAULT_BASE_URL = "https://api.minimaxi.com/v1"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        # 优先使用环境变量，其次使用传入参数，最后使用默认值
        api_key = api_key or os.getenv("MINIMAX_API_KEY")
        base_url = base_url or os.getenv("MINIMAX_BASE_URL") or os.getenv("MINIMAX_API_URL") or self.DEFAULT_BASE_URL
        super().__init__(api_key, base_url)

    def text_to_speech(
        self,
        text: str,
        model: str = "speech-2.8-hd",
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: int = 0,
        emotion: str = "neutral",
        **kwargs
    ) -> Optional[bytes]:
        """
        MiniMax TTS API 调用

        Args:
            text: 待合成文本
            model: TTS 模型
            voice_id: 音色 ID
            speed: 语速
            vol: 音量
            pitch: 音调
            emotion: 情感
            **kwargs: 其他 T2A V2 参数（english_normalization, latex_read, language_boost 等）

        Returns:
            音频字节数据（MP3），失败返回 None
        """
        url = f"{self.base_url}/t2a_v2"

        voice_setting = {
            "voice_id": voice_id,
            "speed": float(speed),
            "vol": float(vol),
            "pitch": int(pitch),
            "emotion": emotion,
        }

        # 可选参数
        if kwargs.get("english_normalization"):
            voice_setting["english_normalization"] = True
        if kwargs.get("latex_read"):
            voice_setting["latex_read"] = True

        audio_setting = {
            "sample_rate": 32000,
            "format": "mp3",
            "channel": 1,
        }

        payload = {
            "model": model,
            "text": text,
            "stream": False,
            "voice_setting": voice_setting,
            "audio_setting": audio_setting,
        }

        # 高级参数
        if kwargs.get("language_boost"):
            payload["language_boost"] = kwargs["language_boost"]
        if kwargs.get("pronunciation_dict"):
            payload["pronunciation_dict"] = kwargs["pronunciation_dict"]
        if kwargs.get("voice_modify"):
            payload["voice_modify"] = kwargs["voice_modify"]

        try:
            response = self._request("POST", url, json=payload)
            result = response.json()

            # 检查业务状态码
            base_resp = result.get("base_resp", {})
            status_code = base_resp.get("status_code")

            if status_code in [1001, 1013, 1021]:
                raise RateLimitError(f"Business rate limited ({status_code})")

            if status_code != 0:
                raise APIResponseError(f"API 返回错误码: {status_code}, 消息: {base_resp.get('status_msg')}")

            # 提取音频数据
            audio_hex = result.get("data", {}).get("audio")
            if not audio_hex:
                raise APIResponseError("响应中未包含音频数据")

            import binascii
            return binascii.unhexlify(audio_hex)

        except (APIClientError, Exception) as e:
            logger.error(f"MiniMax TTS 调用失败: {e}")
            return None

    def generate_text(
        self,
        prompt: str,
        model: str = "M2-preview-1004",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """
        MiniMax 文本生成 API（非流式）

        Args:
            prompt: 提示词
            model: 模型 ID
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            生成的文本，失败返回 None
        """
        url = f"{self.base_url}/text/chatcompletion_v2"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self._request("POST", url, json=payload)
            result = response.json()

            base_resp = result.get("base_resp", {})
            if base_resp.get("status_code") != 0:
                raise APIResponseError(f"API 错误: {base_resp.get('status_msg')}")

            choices = result.get("choices", [])
            if not choices:
                raise APIResponseError("响应中无生成内容")

            return choices[0].get("message", {}).get("content")

        except (APIClientError, Exception) as e:
            logger.error(f"MiniMax 文本生成失败: {e}")
            return None

    def generate_text_stream(
        self,
        prompt: str,
        model: str = "M2-preview-1004",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Iterator[str]:
        """
        MiniMax 文本生成 API（流式）

        Yields: 文本片段
        """
        url = f"{self.base_url}/text/chatcompletion_v2"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json=payload,
                stream=True,
                timeout=60
            )

            for line in response.iter_lines():
                if not line or not line.startswith(b"data:"):
                    continue

                data_str = line.decode("utf-8")[5:].strip()
                if data_str == "[DONE]":
                    break

                import json
                chunk = json.loads(data_str)
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

        except Exception as e:
            logger.error(f"MiniMax 流式生成失败: {e}")
            raise


class QwenClient(BaseAPIClient):
    """Qwen API 客户端（通义千问）"""

    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        api_key = api_key or os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        base_url = base_url or os.getenv("QWEN_BASE_URL") or self.DEFAULT_BASE_URL
        super().__init__(api_key, base_url)

    def generate_text(
        self,
        prompt: str,
        model: str = "qwen-turbo",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Optional[str]:
        """Qwen 文本生成"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = self._request("POST", url, json=payload)
            result = response.json()

            choices = result.get("choices", [])
            if not choices:
                raise APIResponseError("响应中无生成内容")

            return choices[0].get("message", {}).get("content")

        except (APIClientError, Exception) as e:
            logger.error(f"Qwen 文本生成失败: {e}")
            return None

    def text_to_speech(
        self,
        text: str,
        model: str = "qwen3-tts-flash",
        voice: str = "cherry",
        **kwargs
    ) -> Optional[bytes]:
        """
        Qwen TTS API（需要调用方实现，因为不同模型差异较大）
        这里仅提供接口定义
        """
        raise NotImplementedError("Qwen TTS 需要使用具体的引擎实现")


# 便捷工厂函数
def create_minimax_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> MiniMaxClient:
    """创建 MiniMax 客户端"""
    return MiniMaxClient(api_key, base_url)


def create_qwen_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> QwenClient:
    """创建 Qwen 客户端"""
    return QwenClient(api_key, base_url)
