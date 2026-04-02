"""
LLM 生成 + TTS 全流程用例

职责：
- 使用 LLM 生成播客对话脚本
- 解析对话脚本
- 调用 TTS 引擎批量合成
- FFmpeg 混音
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict
import logging

from ..entities import EngineResult
from .dialogue_speech import DialogueSpeechUseCase
from .tts_use_cases import TTSEngineInterface
from ..adapters.llm_adapters import LLMEngineInterface
from ..adapters.audio_adapters import FFmpegAudioProcessor

logger = logging.getLogger(__name__)

# LLM 生成播客脚本的系统提示词
_PODCAST_SYSTEM_PROMPT = """你是一个播客脚本写作助手。请根据用户给定的主题，生成一段两个角色的对话脚本。

要求：
- 生成2-3个角色之间的自然对话
- 每个角色有独特的说话风格
- 内容要有深度，避免浅薄
- 输出格式：每行一个角色发言，格式为 [角色名]: 发言内容
- 不要使用方括号或特殊格式包裹角色名以外的内容
- 总字数控制在300-500字左右

示例格式：
[Alex]: 开场白，介绍话题
[Sam]: 回应并引入第一个观点
[Alex]: 深入讨论
[Sam]: 提供另一个视角
"""


@dataclass
class StudioPodcastUseCase:
    """
    播客工作室用例

    全流程：LLM 生成脚本 -> 解析 -> TTS -> 混音

    Example:
        >>> use_case = StudioPodcastUseCase(
        ...     llm_engine=QwenLLMEngine(api_key="..."),
        ...     tts_engine=MiniMaxTTSEngine(api_key="...", group_id="..."),
        ...     audio_processor=FFmpegAudioProcessor(),
        ... )
        >>> result = use_case.execute(
        ...     topic="人工智能的未来",
        ...     output_file=Path("podcast.mp3"),
        ... )
        >>> result.success
        True
    """

    llm_engine: LLMEngineInterface
    tts_engine: TTSEngineInterface
    audio_processor: FFmpegAudioProcessor

    def execute(
        self,
        topic: str,
        output_file: Path,
        roles_config: Optional[Dict] = None,
        bgm_file: Optional[Path] = None,
        sample_rate: int = 32000,
        custom_prompt: Optional[str] = None,
    ) -> EngineResult:
        """
        执行播客生成全流程

        Args:
            topic: 播客主题
            output_file: 输出音频文件
            roles_config: 角色音色映射，如 {"Alex": "male-qn-qingse", "Sam": "male-qn-jingpin"}
            bgm_file: 背景音乐文件
            sample_rate: 采样率
            custom_prompt: 自定义提示词（可选）

        Returns:
            EngineResult: 生成结果
        """
        # 1. 检查 LLM 可用性
        if not self.llm_engine.is_available():
            return EngineResult.failure("LLM 引擎未配置 API Key")

        # 2. 构建提示词
        if custom_prompt:
            user_prompt = custom_prompt
        else:
            user_prompt = f"请生成一段关于「{topic}」的播客对话脚本。"

        full_prompt = f"{_PODCAST_SYSTEM_PROMPT}\n\n{user_prompt}"

        # 3. 调用 LLM 生成脚本
        logger.info(f"正在生成播客脚本: {topic}")
        script_text = self.llm_engine.generate(
            prompt=full_prompt,
            temperature=0.7,
            max_tokens=2000,
        )

        if not script_text:
            return EngineResult.failure("LLM 生成脚本失败")

        logger.info(f"LLM 生成脚本成功，长度: {len(script_text)} 字符")

        # 4. 解析对话（验证格式）
        from .dialogue_speech import parse_dialogue_segments

        segments = parse_dialogue_segments(script_text, roles_config)
        if not segments:
            return EngineResult.failure("LLM 生成的脚本无法解析为对话格式")

        logger.info(f"解析到 {len(segments)} 个对话片段")

        # 5. 委托 DialogueSpeechUseCase 执行 TTS
        dialogue_uc = DialogueSpeechUseCase(
            engine=self.tts_engine,
            audio_processor=self.audio_processor,
        )

        return dialogue_uc.execute(
            dialogue_script=script_text,
            output_file=output_file,
            roles_config=roles_config,
            bgm_file=bgm_file,
            sample_rate=sample_rate,
        )
