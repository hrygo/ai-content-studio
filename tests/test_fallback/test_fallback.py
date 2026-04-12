"""Fallback 测试"""
from voiceforge.fallback import FallbackExecutor, get_fallback_engine, get_fallback_llm_engine
from voiceforge.entities import EngineResult
from pathlib import Path


class TestFallbackMapping:
    def test_tts_fallback(self):
        assert get_fallback_engine("minimax") == "qwen_tts"
        assert get_fallback_engine("qwen_tts") == "minimax"
        assert get_fallback_engine("qwen_omni") == "minimax"

    def test_tts_no_fallback(self):
        assert get_fallback_engine("unknown") is None

    def test_llm_fallback(self):
        assert get_fallback_llm_engine("minimax") == "qwen"
        assert get_fallback_llm_engine("qwen") == "minimax"


class TestFallbackExecutor:
    def test_primary_success(self):
        executor = FallbackExecutor(primary=lambda: EngineResult.ok(Path("out.mp3")))
        result = executor.execute()
        assert result.success

    def test_fallback_on_failure(self):
        executor = FallbackExecutor(
            primary=lambda: EngineResult.fail("1008 insufficient"),
            fallback=lambda: EngineResult.ok(Path("out.mp3")),
        )
        result = executor.execute()
        assert result.success

    def test_no_fallback_configured(self):
        executor = FallbackExecutor(primary=lambda: EngineResult.fail("error"))
        result = executor.execute()
        assert not result.success

    def test_no_infinite_loop(self):
        call_count = 0

        def bad_primary():
            nonlocal call_count
            call_count += 1
            return EngineResult.fail("1008 insufficient")

        executor = FallbackExecutor(primary=bad_primary, fallback=bad_primary)
        executor.execute()
        assert call_count <= 3  # primary + fallback + one retry
