"""
SSE (Server-Sent Events) 解析工具
统一的 SSE 流解析逻辑，避免代码重复
"""
import json
from typing import Iterator, Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)


def parse_sse_stream(
    response,
    decoder: Callable[[str], Any] = json.loads,
    done_marker: str = "[DONE]"
) -> Iterator[Any]:
    """
    解析 SSE 流并 yield 解码后的数据块

    Args:
        response: requests.Response 对象
        decoder: 解码函数（默认: json.loads）
        done_marker: SSE 结束标记（默认: "[DONE]"）

    Yields:
        Any: 解码后的数据块

    Example:
        >>> for chunk in parse_sse_stream(response):
        ...     print(chunk)
    """
    for line in response.iter_lines():
        if not line or not line.startswith(b"data:"):
            continue

        data_str = line.decode("utf-8")[5:].strip()
        if not data_str or data_str == done_marker:
            continue

        try:
            chunk = decoder(data_str)
            yield chunk
        except Exception as e:
            logger.debug(f"解码 SSE chunk 失败: {e}, data={data_str[:50]}")
            continue


def parse_sse_audio_stream(
    response,
    get_audio_data: Callable[[Any], Optional[str]],
    get_text_content: Optional[Callable[[Any], Optional[str]]] = None,
    done_marker: str = "[DONE]"
) -> tuple[list, str]:
    """
    解析包含音频数据的 SSE 流

    Args:
        response: requests.Response 对象
        get_audio_data: 从 chunk 提取音频数据的函数
        get_text_content: 从 chunk 提取文本内容的函数（可选）
        done_marker: SSE 结束标记

    Returns:
        tuple[list, str]: (音频数据列表, 完整文本内容)

    Example:
        >>> chunks, text = parse_sse_audio_stream(
        ...     response,
        ...     get_audio_data=lambda chunk: chunk.get("audio", {}).get("data"),
        ...     get_text_content=lambda chunk: chunk.get("delta", {}).get("content")
        ... )
    """
    audio_chunks = []
    text_content = ""

    for chunk in parse_sse_stream(response, done_marker=done_marker):
        # 提取音频数据
        audio_data = get_audio_data(chunk)
        if audio_data:
            audio_chunks.append(audio_data)

        # 提取文本内容
        if get_text_content:
            text = get_text_content(chunk)
            if text:
                text_content += text

    return audio_chunks, text_content
