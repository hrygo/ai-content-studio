"""
Fallback 机制边缘测试
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.entities import AudioSegment, EngineResult
from src.entities.errors import ErrorType
from src.utils.fallback import (
    FallbackExecutor,
    get_fallback_engine,
    get_fallback_llm_engine,
)
from src.use_cases.tts_use_cases import BatchSynthesizeUseCase


class TestErrorTypeClassification:
    """ErrorType.classify() 边缘测试"""

    @pytest.mark.parametrize(
        "error_msg,expected",
        [
            # RETRYABLE: 网络/超时/限流
            ("Request timeout", ErrorType.RETRYABLE),
            ("连接超时", ErrorType.RETRYABLE),
            ("Connection reset", ErrorType.RETRYABLE),
            ("网络错误", ErrorType.RETRYABLE),
            ("Rate limit exceeded", ErrorType.RETRYABLE),
            ("请求限流", ErrorType.RETRYABLE),
            # FALLBACK: 余额/音色/API 错误
            ("Insufficient balance", ErrorType.FALLBACK),
            ("余额不足", ErrorType.FALLBACK),
            ("Voice not licensed", ErrorType.FALLBACK),
            ("invalid voice id", ErrorType.FALLBACK),
            ("API error occurred", ErrorType.FALLBACK),
            ("API请求失败", ErrorType.FALLBACK),
            # FATAL: 未知错误
            ("Something went wrong", ErrorType.FATAL),
            ("未知错误", ErrorType.FATAL),
        ],
    )
    def test_error_type_classification(self, error_msg, expected):
        assert ErrorType.classify(error_msg) == expected

    def test_none_error_returns_fatal(self):
        assert ErrorType.classify(None) == ErrorType.FATAL

    def test_empty_error_returns_fatal(self):
        assert ErrorType.classify("") == ErrorType.FATAL

    def test_case_insensitive(self):
        assert ErrorType.classify("TIMEOUT") == ErrorType.RETRYABLE
        assert ErrorType.classify("Timeout") == ErrorType.RETRYABLE

    def test_priority_mixed_keywords(self):
        # 超时优先于 API 错误
        assert ErrorType.classify("API timeout occurred") == ErrorType.RETRYABLE
        # 余额优先于通用 API 错误
        assert ErrorType.classify("余额不足") == ErrorType.FALLBACK


class TestFallbackExecutor:
    """FallbackExecutor 边缘测试"""

    def test_success_result_no_fallback(self):
        success_result = Mock(success=True, error_message=None)
        fallback_mock = Mock()

        executor = FallbackExecutor(
            primary=lambda: success_result,
            fallback=fallback_mock,
        )

        result = executor.execute()
        assert result.success is True
        fallback_mock.assert_not_called()

    def test_retryable_error_no_fallback_by_default(self):
        retry_result = Mock(success=False, error_message="timeout")

        executor = FallbackExecutor(
            primary=lambda: retry_result,
            fallback=lambda: Mock(success=True),
        )

        result = executor.execute()
        assert result.error_message == "timeout"

    def test_fallback_error_triggers_fallback(self):
        primary_result = Mock(success=False, error_message="Insufficient balance")
        fallback_result = Mock(success=True, error_message=None)

        executor = FallbackExecutor(
            primary=lambda: primary_result,
            fallback=lambda: fallback_result,
        )

        result = executor.execute()
        assert result.success is True

    def test_fallback_only_once(self):
        """fallback 只尝试一次，防止无限循环"""
        primary_calls = [0]
        fallback_calls = [0]

        def primary():
            primary_calls[0] += 1
            return Mock(success=False, error_message="balance insufficient")

        def fallback():
            fallback_calls[0] += 1
            return Mock(success=False, error_message="fallback also failed")

        executor = FallbackExecutor(primary=primary, fallback=fallback)
        result = executor.execute()

        # 主函数只在 execute 入口调用一次
        assert primary_calls[0] == 1
        # fallback 被调用一次
        assert fallback_calls[0] == 1
        # fallback 失败时返回其失败结果
        assert result.error_message == "fallback also failed"

    def test_primary_exception_triggers_fallback(self):
        def primary():
            raise RuntimeError("Primary engine crashed")

        def fallback():
            return Mock(success=True, error_message=None)

        executor = FallbackExecutor(primary=primary, fallback=fallback)
        result = executor.execute()
        assert result.success is True

    def test_no_fallback_configured(self):
        primary_result = Mock(success=False, error_message="balance insufficient")

        executor = FallbackExecutor(
            primary=lambda: primary_result,
            fallback=None,
        )

        result = executor.execute()
        assert result.error_message == "balance insufficient"

    def test_custom_should_fallback_func(self):
        def always_fallback(error_msg):
            return True

        primary_result = Mock(success=False, error_message="any error")
        fallback_result = Mock(success=True, error_message=None)

        executor = FallbackExecutor(
            primary=lambda: primary_result,
            fallback=lambda: fallback_result,
            should_fallback_func=always_fallback,
        )

        result = executor.execute()
        assert result.success is True


class TestGetFallbackEngine:
    """get_fallback_engine() 边缘测试"""

    @pytest.mark.parametrize(
        "engine,expected",
        [
            ("minimax", "qwen_tts"),
            ("qwen_tts", "minimax"),
            ("qwen_omni", "minimax"),
            ("qwen", "minimax"),
        ],
    )
    def test_known_engine_has_fallback(self, engine, expected):
        assert get_fallback_engine(engine) == expected

    def test_unknown_engine_returns_none(self):
        assert get_fallback_engine("unknown") is None
        assert get_fallback_engine("") is None

    def test_case_sensitive(self):
        assert get_fallback_engine("Minimax") is None
        assert get_fallback_engine("MINIMAX") is None


class TestGetFallbackLLMEngine:
    """get_fallback_llm_engine() 边缘测试"""

    @pytest.mark.parametrize(
        "engine,expected",
        [
            ("minimax", "qwen"),
            ("MiniMaxLLMEngine", "QwenLLMEngine"),
            ("qwen", "minimax"),
            ("QwenLLMEngine", "MiniMaxLLMEngine"),
        ],
    )
    def test_known_llm_engine_has_fallback(self, engine, expected):
        assert get_fallback_llm_engine(engine) == expected

    def test_unknown_engine_returns_none(self):
        assert get_fallback_llm_engine("unknown") is None
        assert get_fallback_llm_engine("") is None


class TestBatchSynthesizeWithFallback:
    """BatchSynthesizeUseCase Fallback 边缘测试"""

    def test_no_fallback_engine_configured(self, mock_minimax_engine, mock_audio_processor, temp_output_dir):
        """未配置 fallback 时失败直接返回"""
        segments = [AudioSegment(text="测试文本", voice_id="male-qn-qingse")]

        mock_minimax_engine.synthesize.return_value = EngineResult.failure(
            error_message="Insufficient balance",
            engine_name="minimax",
        )

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
            fallback_engine=None,
        )

        result = use_case.execute(
            segments=segments,
            output_file=temp_output_dir / "output.mp3",
        )

        assert not result.success
        assert "Insufficient balance" in result.error_message

    def test_fallback_engine_on_fatal_error(self, mock_minimax_engine, mock_qwen_engine, mock_audio_processor, temp_output_dir):
        """FATAL 错误不触发 fallback"""
        segments = [AudioSegment(text="测试文本", voice_id="male-qn-qingse")]

        mock_minimax_engine.synthesize.return_value = EngineResult.failure(
            error_message="Unknown error",
            engine_name="minimax",
        )

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
            fallback_engine=mock_qwen_engine,
        )

        result = use_case.execute(
            segments=segments,
            output_file=temp_output_dir / "output.mp3",
        )

        assert not result.success
        mock_qwen_engine.synthesize.assert_not_called()

    @pytest.mark.parametrize(
        "error_message",
        ["Insufficient balance", "Voice not licensed"],
    )
    def test_fallback_engine_on_classified_error(
        self, error_message, mock_minimax_engine, mock_qwen_engine,
        mock_audio_processor, temp_output_dir
    ):
        """FALLBACK 类型错误触发 fallback"""
        segments = [
            AudioSegment(text="测试文本", voice_id="male-qn-qingse"),
            AudioSegment(text="第二段", voice_id="female-shaonv"),
        ]

        mock_minimax_engine.synthesize.return_value = EngineResult.failure(
            error_message=error_message,
            engine_name="minimax",
        )
        mock_qwen_engine.synthesize.side_effect = [
            EngineResult.success(file_path=temp_output_dir / "qwen_temp1.mp3",
                                 duration=2.0, engine_name="qwen"),
            EngineResult.success(file_path=temp_output_dir / "qwen_temp2.mp3",
                                 duration=2.0, engine_name="qwen"),
        ]
        mock_audio_processor.merge_audio_files.return_value = EngineResult.success(
            file_path=temp_output_dir / "output.mp3",
            duration=4.0, engine_name="qwen",
        )

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
            fallback_engine=mock_qwen_engine,
        )

        result = use_case.execute(
            segments=segments,
            output_file=temp_output_dir / "output.mp3",
        )

        assert result.success
        assert mock_minimax_engine.synthesize.call_count == 2
        assert mock_qwen_engine.synthesize.call_count == 2
        mock_audio_processor.merge_audio_files.assert_called_once()

    def test_both_engines_fail(self, mock_minimax_engine, mock_qwen_engine, mock_audio_processor, temp_output_dir):
        """主引擎和 fallback 都失败"""
        segments = [AudioSegment(text="测试文本", voice_id="male-qn-qingse")]

        mock_minimax_engine.synthesize.return_value = EngineResult.failure(
            error_message="Insufficient balance",
            engine_name="minimax",
        )
        mock_qwen_engine.synthesize.return_value = EngineResult.failure(
            error_message="API error",
            engine_name="qwen",
        )

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
            fallback_engine=mock_qwen_engine,
        )

        result = use_case.execute(
            segments=segments,
            output_file=temp_output_dir / "output.mp3",
        )

        assert not result.success
        mock_minimax_engine.synthesize.assert_called_once()
        mock_qwen_engine.synthesize.assert_called_once()

    def test_fallback_exception_handled(self, mock_minimax_engine, mock_audio_processor, temp_output_dir):
        """fallback 引擎异常被捕获"""
        segments = [AudioSegment(text="测试文本", voice_id="male-qn-qingse")]

        mock_minimax_engine.synthesize.return_value = EngineResult.failure(
            error_message="Insufficient balance",
            engine_name="minimax",
        )
        fallback_engine = Mock()
        fallback_engine.synthesize.side_effect = RuntimeError("Fallback crashed")
        fallback_engine.get_engine_name.return_value = "fallback"

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
            fallback_engine=fallback_engine,
        )

        result = use_case.execute(
            segments=segments,
            output_file=temp_output_dir / "output.mp3",
        )

        assert not result.success
        assert "Fallback crashed" in result.error_message
        mock_minimax_engine.synthesize.assert_called_once()


class TestBatchSynthesizeEdgeCases:
    """BatchSynthesizeUseCase 其他边缘测试"""

    def test_single_segment_no_merge(self, mock_minimax_engine, mock_audio_processor, temp_output_dir):
        """单个片段不触发合并"""
        temp_file = temp_output_dir / "temp_single.mp3"
        temp_file.touch()

        mock_minimax_engine.synthesize.return_value = EngineResult.success(
            file_path=temp_file,
            duration=2.0,
            engine_name="minimax",
        )

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
        )

        result = use_case.execute(
            segments=[AudioSegment(text="单独片段", voice_id="male-qn-qingse")],
            output_file=temp_output_dir / "output.mp3",
            merge=False,
        )

        assert result.success
        mock_minimax_engine.synthesize.assert_called_once()
        mock_audio_processor.merge_audio_files.assert_not_called()

    def test_two_segments_both_succeed(self, mock_minimax_engine, mock_audio_processor, temp_output_dir):
        """两个片段都成功合成"""
        segments = [
            AudioSegment(text="第一段", voice_id="male-qn-qingse"),
            AudioSegment(text="第二段", voice_id="female-shaonv"),
        ]

        mock_minimax_engine.synthesize.side_effect = [
            EngineResult.success(temp_output_dir / "temp1.mp3", duration=2.0),
            EngineResult.success(temp_output_dir / "temp2.mp3", duration=3.0),
        ]
        mock_audio_processor.merge_audio_files.return_value = EngineResult.success(
            temp_output_dir / "output.mp3", duration=5.0
        )

        use_case = BatchSynthesizeUseCase(
            engine=mock_minimax_engine,
            audio_processor=mock_audio_processor,
        )

        result = use_case.execute(
            segments=segments,
            output_file=temp_output_dir / "output.mp3",
            merge=True,
        )

        assert result.success
        assert mock_minimax_engine.synthesize.call_count == 2
        mock_audio_processor.merge_audio_files.assert_called_once()
