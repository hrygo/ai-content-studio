"""播客工作室用例 — LLM 生成脚本 → TTS → 混音"""
import logging
from dataclasses import dataclass
from pathlib import Path

from voiceforge.entities import EngineResult, ErrorType
from voiceforge.protocols.engine import TTSEngine, LLMEngine
from voiceforge.protocols.processor import AudioProcessor
from .dialogue import DialogueSpeechUseCase

logger = logging.getLogger(__name__)

_PODCAST_SYSTEM_PROMPT = """你是一个播客脚本写作助手。请根据用户给定的主题，生成一段两个角色的对话脚本。

要求：
- 生成2-3个角色之间的自然对话
- 每个角色有独特的说话风格
- 内容要有深度，避免浅薄
- 输出格式：每行一个角色发言，格式为 [角色名]: 发言内容
- 总字数控制在300-500字左右

示例：
[Alex]: 开场白，介绍话题
[Sam]: 回应并引入第一个观点
"""


@dataclass
class StudioPodcastUseCase:
    """播客全流程：LLM 生成 → TTS → 混音（含 LLM/TTS 双 fallback）"""

    llm_engine: LLMEngine
    tts_engine: TTSEngine
    audio_processor: AudioProcessor
    fallback_llm: LLMEngine | None = None
    fallback_tts: TTSEngine | None = None

    def execute(
        self,
        topic: str,
        output_file: Path,
        roles_config: dict | None = None,
        bgm_file: Path | None = None,
        sample_rate: int = 32000,
        custom_prompt: str | None = None,
    ) -> EngineResult:
        if not self.llm_engine.is_available():
            return EngineResult.fail("LLM 引擎未配置 API Key")

        # 1. 生成脚本
        user_prompt = custom_prompt or f"请生成一段关于「{topic}」的播客对话脚本。"
        full_prompt = f"{_PODCAST_SYSTEM_PROMPT}\n\n{user_prompt}"

        logger.info(f"正在生成播客脚本: {topic}")
        script_text = self._generate_script(full_prompt)
        if not script_text:
            return EngineResult.fail("LLM 生成脚本失败（已尝试 fallback）")

        logger.info(f"脚本生成成功，{len(script_text)} 字符")

        # 2. 委托对话用例执行 TTS
        dialogue_uc = DialogueSpeechUseCase(
            engine=self.tts_engine,
            audio_processor=self.audio_processor,
            fallback_engine=self.fallback_tts,
        )
        return dialogue_uc.execute(
            dialogue_script=script_text,
            output_file=output_file,
            roles_config=roles_config,
            bgm_file=bgm_file,
            sample_rate=sample_rate,
        )

    def _generate_script(self, prompt: str) -> str | None:
        # 主 LLM
        try:
            result = self.llm_engine.generate(prompt=prompt, temperature=0.7, max_tokens=2000)
            if result:
                return result
        except Exception as e:
            logger.warning(f"主 LLM 失败: {e}")

        # Fallback LLM
        if self.fallback_llm and self.fallback_llm.is_available():
            logger.warning("切换到 fallback LLM")
            try:
                return self.fallback_llm.generate(prompt=prompt, temperature=0.7, max_tokens=2000)
            except Exception as e:
                logger.error(f"Fallback LLM 也失败: {e}")

        return None
