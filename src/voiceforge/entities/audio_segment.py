"""音频片段实体"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioSegment:
    """待合成的音频片段"""
    text: str
    voice_id: str = "male-qn-qingse"
