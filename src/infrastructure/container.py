"""
依赖注入容器
"""
from dataclasses import dataclass, field
from typing import Optional, Dict
import os

from ..adapters.tts_adapters import MiniMaxTTSEngine, QwenOmniTTSEngine
from ..adapters.audio_adapters import FFmpegAudioProcessor
from ..adapters.llm_adapters import MiniMaxLLMEngine, QwenLLMEngine, BaseLLMEngine
from ..use_cases.tts_use_cases import SynthesizeSpeechUseCase, BatchSynthesizeUseCase
from ..use_cases.dialogue_speech import DialogueSpeechUseCase
from ..use_cases.studio_podcast import StudioPodcastUseCase


@dataclass
class Container:
    """
    依赖注入容器

    职责：
    - 管理组件生命周期
    - 提供依赖注入
    - 配置管理

    Example:
        >>> container = Container.from_env()
        >>> use_case = container.synthesize_speech_use_case()
        >>> result = use_case.execute(text="测试", output_file=Path("test.mp3"))
    """

    # TTS 引擎
    minimax_engine: Optional[MiniMaxTTSEngine] = None
    qwen_engine: Optional[QwenOmniTTSEngine] = None

    # LLM 引擎
    minimax_llm_engine: Optional[MiniMaxLLMEngine] = None
    qwen_llm_engine: Optional[QwenLLMEngine] = None

    # 音频处理器
    audio_processor: Optional[FFmpegAudioProcessor] = None

    # 用例缓存（按引擎类型）
    _use_case_cache: Dict[str, SynthesizeSpeechUseCase] = field(default_factory=dict)
    _batch_use_case_cache: Dict[str, BatchSynthesizeUseCase] = field(default_factory=dict)
    _dialogue_use_case_cache: Dict[str, DialogueSpeechUseCase] = field(default_factory=dict)
    _studio_use_case_cache: Dict[str, StudioPodcastUseCase] = field(default_factory=dict)

    # 配置
    config: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Container":
        """
        从环境变量创建容器

        Returns:
            Container: 配置好的容器实例
        """
        container = cls()

        # MiniMax TTS 配置
        minimax_api_key = os.getenv("MINIMAX_API_KEY")
        minimax_group_id = os.getenv("MINIMAX_GROUP_ID")
        if minimax_api_key:
            # 如果没有 MINIMAX_GROUP_ID，尝试从 API Key 或其他来源推断
            # 某些 Anthropic 兼容代理可能不需要 group_id
            if not minimax_group_id:
                # 尝试使用默认值或从 API key 中提取
                # 对于代理模式，group_id 可能为 None
                minimax_group_id = os.getenv("MINIMAX_GROUP_ID", "default")

            container.minimax_engine = MiniMaxTTSEngine(
                api_key=minimax_api_key,
                group_id=minimax_group_id,
            )

        # Qwen TTS 配置（支持 QWEN_API_KEY 或 DASHSCOPE_API_KEY）
        qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if qwen_api_key:
            container.qwen_engine = QwenOmniTTSEngine(
                api_key=qwen_api_key,
            )

        # MiniMax LLM 配置（复用 minimax_api_key）
        if minimax_api_key:
            container.minimax_llm_engine = MiniMaxLLMEngine(api_key=minimax_api_key)

        # Qwen LLM 配置
        qwen_llm_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        if qwen_llm_key:
            container.qwen_llm_engine = QwenLLMEngine(api_key=qwen_llm_key)

        # 音频处理器
        container.audio_processor = FFmpegAudioProcessor()

        return container

    def synthesize_speech_use_case(
        self, engine_type: str = "minimax"
    ) -> SynthesizeSpeechUseCase:
        """
        获取单次合成用例（按引擎类型缓存）

        Args:
            engine_type: 引擎类型（minimax 或 qwen）

        Returns:
            SynthesizeSpeechUseCase: 用例实例
        """
        if engine_type not in self._use_case_cache:
            engine = self._get_engine(engine_type)
            self._use_case_cache[engine_type] = SynthesizeSpeechUseCase(engine=engine)

        return self._use_case_cache[engine_type]

    def batch_synthesize_use_case(
        self, engine_type: str = "minimax"
    ) -> BatchSynthesizeUseCase:
        """
        获取批量合成用例（按引擎类型缓存）

        Args:
            engine_type: 引擎类型（minimax 或 qwen）

        Returns:
            BatchSynthesizeUseCase: 用例实例
        """
        if engine_type not in self._batch_use_case_cache:
            engine = self._get_engine(engine_type)
            self._batch_use_case_cache[engine_type] = BatchSynthesizeUseCase(
                engine=engine, audio_processor=self.audio_processor
            )

        return self._batch_use_case_cache[engine_type]

    def dialogue_speech_use_case(self, engine_type: str = "minimax") -> DialogueSpeechUseCase:
        """
        获取对话脚本 TTS 用例（按引擎类型缓存）

        Args:
            engine_type: TTS 引擎类型（minimax 或 qwen）

        Returns:
            DialogueSpeechUseCase: 用例实例
        """
        if engine_type not in self._dialogue_use_case_cache:
            self._dialogue_use_case_cache[engine_type] = DialogueSpeechUseCase(
                engine=self._get_engine(engine_type),
                audio_processor=self.audio_processor,
            )
        return self._dialogue_use_case_cache[engine_type]

    def studio_podcast_use_case(
        self, llm: str = "minimax", tts: str = "minimax"
    ) -> StudioPodcastUseCase:
        """
        获取播客工作室用例（按 LLM+TTS 组合缓存）

        Args:
            llm: LLM 引擎类型（minimax 或 qwen）
            tts: TTS 引擎类型（minimax 或 qwen）

        Returns:
            StudioPodcastUseCase: 用例实例
        """
        cache_key = f"{llm}_{tts}"
        if cache_key not in self._studio_use_case_cache:
            llm_engine = self.get_llm_engine(llm)
            tts_engine = self._get_engine(tts)
            self._studio_use_case_cache[cache_key] = StudioPodcastUseCase(
                llm_engine=llm_engine,
                tts_engine=tts_engine,
                audio_processor=self.audio_processor,
            )
        return self._studio_use_case_cache[cache_key]

    def _get_engine(self, engine_type: str):
        """获取 TTS 引擎"""
        if engine_type == "minimax":
            if self.minimax_engine is None:
                raise ValueError("MiniMax 引擎未配置，请设置 MINIMAX_API_KEY 和 MINIMAX_GROUP_ID")
            return self.minimax_engine
        elif engine_type == "qwen":
            if self.qwen_engine is None:
                raise ValueError("Qwen 引擎未配置，请设置 QWEN_API_KEY")
            return self.qwen_engine
        elif engine_type == "qwen_tts":
            # 需要 QwenTTSEngine - 暂不支持，返回 qwen_engine 作为 fallback
            if self.qwen_engine is None:
                raise ValueError("Qwen TTS 引擎未配置，请设置 QWEN_API_KEY")
            return self.qwen_engine
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")

    def get_llm_engine(self, engine_name: str) -> BaseLLMEngine:
        """获取 LLM 引擎"""
        if engine_name == "minimax":
            if self.minimax_llm_engine is None:
                raise ValueError("MiniMax LLM 未配置，请设置 MINIMAX_API_KEY")
            return self.minimax_llm_engine
        elif engine_name in ("qwen", "qwen_omni"):
            if self.qwen_llm_engine is None:
                raise ValueError("Qwen LLM 未配置，请设置 QWEN_API_KEY 或 DASHSCOPE_API_KEY")
            return self.qwen_llm_engine
        else:
            raise ValueError(f"不支持的 LLM 引擎: {engine_name}")

    def cleanup(self):
        """清理资源"""
        if self.audio_processor is not None:
            self.audio_processor.cleanup()
