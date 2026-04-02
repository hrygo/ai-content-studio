"""
依赖注入容器
"""
from dataclasses import dataclass, field
from typing import Optional, Dict
import os

from ..adapters.tts_adapters import MiniMaxTTSEngine, QwenOmniTTSEngine
from ..adapters.audio_adapters import FFmpegAudioProcessor
from ..use_cases.tts_use_cases import SynthesizeSpeechUseCase, BatchSynthesizeUseCase


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

    # 音频处理器
    audio_processor: Optional[FFmpegAudioProcessor] = None

    # 用例缓存（按引擎类型）
    _use_case_cache: Dict[str, SynthesizeSpeechUseCase] = field(default_factory=dict)
    _batch_use_case_cache: Dict[str, BatchSynthesizeUseCase] = field(default_factory=dict)

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

        # MiniMax 配置
        minimax_api_key = os.getenv("MINIMAX_API_KEY")
        minimax_group_id = os.getenv("MINIMAX_GROUP_ID")
        if minimax_api_key and minimax_group_id:
            container.minimax_engine = MiniMaxTTSEngine(
                api_key=minimax_api_key,
                group_id=minimax_group_id,
            )

        # Qwen 配置
        qwen_api_key = os.getenv("QWEN_API_KEY")
        if qwen_api_key:
            container.qwen_engine = QwenOmniTTSEngine(
                api_key=qwen_api_key,
            )

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
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")

    def cleanup(self):
        """清理资源"""
        if self.audio_processor is not None:
            self.audio_processor.cleanup()
