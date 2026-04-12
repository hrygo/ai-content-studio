"""依赖注入容器"""
import os
import logging
from dataclasses import dataclass, field

from voiceforge.engines.tts import MiniMaxTTSEngine, QwenTTSEngine, QwenOmniTTSEngine
from voiceforge.engines.llm import MiniMaxLLMEngine, QwenLLMEngine
from voiceforge.audio.processor import FFmpegAudioProcessor
from voiceforge.use_cases.synthesize import SynthesizeSpeechUseCase, BatchSynthesizeUseCase
from voiceforge.use_cases.dialogue import DialogueSpeechUseCase
from voiceforge.use_cases.podcast import StudioPodcastUseCase

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """依赖注入容器（简洁 factory 模式）"""

    audio_processor: FFmpegAudioProcessor = field(default_factory=FFmpegAudioProcessor)

    # 引擎缓存
    _tts_engines: dict[str, object] = field(default_factory=dict)
    _llm_engines: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Container":
        """从环境变量创建容器"""
        return cls()

    # -- TTS 引擎 --
    def get_tts_engine(self, engine_type: str):
        """获取或创建 TTS 引擎（带缓存）"""
        from voiceforge.entities.enums import TTSEngineType
        resolved = TTSEngineType.from_string(engine_type).resolve().value

        if resolved not in self._tts_engines:
            self._tts_engines[resolved] = self._create_tts_engine(resolved)
        return self._tts_engines[resolved]

    def _create_tts_engine(self, engine_type: str):
        if engine_type == "minimax":
            api_key = os.getenv("MINIMAX_API_KEY")
            if not api_key:
                raise ValueError("请设置 MINIMAX_API_KEY")
            group_id = os.getenv("MINIMAX_GROUP_ID", "default")
            return MiniMaxTTSEngine(api_key=api_key, group_id=group_id)

        elif engine_type == "qwen_tts":
            api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("请设置 QWEN_API_KEY 或 DASHSCOPE_API_KEY")
            return QwenTTSEngine(api_key=api_key)

        elif engine_type == "qwen_omni":
            api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("请设置 QWEN_API_KEY 或 DASHSCOPE_API_KEY")
            return QwenOmniTTSEngine(api_key=api_key)

        raise ValueError(f"不支持的 TTS 引擎: {engine_type}")

    # -- LLM 引擎 --
    def get_llm_engine(self, engine_name: str):
        if engine_name not in self._llm_engines:
            self._llm_engines[engine_name] = self._create_llm_engine(engine_name)
        return self._llm_engines[engine_name]

    def _create_llm_engine(self, engine_name: str):
        if engine_name == "minimax":
            api_key = os.getenv("MINIMAX_API_KEY")
            if not api_key:
                raise ValueError("请设置 MINIMAX_API_KEY")
            return MiniMaxLLMEngine(api_key=api_key)

        elif engine_name in ("qwen", "qwen_omni"):
            api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("请设置 QWEN_API_KEY 或 DASHSCOPE_API_KEY")
            return QwenLLMEngine(api_key=api_key)

        raise ValueError(f"不支持的 LLM 引擎: {engine_name}")

    # -- Fallback 引擎 --
    def get_fallback_tts(self, engine_type: str):
        from voiceforge.fallback.executor import get_fallback_engine
        fallback_name = get_fallback_engine(engine_type)
        if not fallback_name:
            return None
        try:
            return self.get_tts_engine(fallback_name)
        except ValueError:
            return None

    def get_fallback_llm(self, engine_name: str):
        from voiceforge.fallback.executor import get_fallback_llm_engine
        fallback_name = get_fallback_llm_engine(engine_name)
        if not fallback_name:
            return None
        try:
            return self.get_llm_engine(fallback_name)
        except ValueError:
            return None

    # -- Use Case 工厂 --
    def synthesize_use_case(self, engine_type: str = "minimax") -> SynthesizeSpeechUseCase:
        return SynthesizeSpeechUseCase(engine=self.get_tts_engine(engine_type))

    def batch_use_case(self, engine_type: str = "minimax") -> BatchSynthesizeUseCase:
        return BatchSynthesizeUseCase(
            engine=self.get_tts_engine(engine_type),
            audio_processor=self.audio_processor,
            fallback_engine=self.get_fallback_tts(engine_type),
        )

    def dialogue_use_case(self, engine_type: str = "minimax") -> DialogueSpeechUseCase:
        return DialogueSpeechUseCase(
            engine=self.get_tts_engine(engine_type),
            audio_processor=self.audio_processor,
            fallback_engine=self.get_fallback_tts(engine_type),
        )

    def podcast_use_case(
        self, llm: str = "minimax", tts: str = "minimax",
    ) -> StudioPodcastUseCase:
        return StudioPodcastUseCase(
            llm_engine=self.get_llm_engine(llm),
            tts_engine=self.get_tts_engine(tts),
            audio_processor=self.audio_processor,
            fallback_llm=self.get_fallback_llm(llm),
            fallback_tts=self.get_fallback_tts(tts),
        )

    def cleanup(self) -> None:
        self.audio_processor.cleanup()
