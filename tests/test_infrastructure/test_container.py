"""Infrastructure 测试"""
from unittest.mock import patch
from voiceforge.infrastructure.container import Container


class TestContainer:
    def test_from_env(self):
        container = Container.from_env()
        assert container.audio_processor is not None

    @patch.dict("os.environ", {"MINIMAX_API_KEY": "test", "MINIMAX_GROUP_ID": "test"})
    def test_get_minimax_tts(self):
        container = Container.from_env()
        engine = container.get_tts_engine("minimax")
        assert engine.get_engine_name() == "minimax"

    @patch.dict("os.environ", {"QWEN_API_KEY": "test"})
    def test_get_qwen_tts(self):
        container = Container.from_env()
        engine = container.get_tts_engine("qwen_tts")
        assert engine.get_engine_name() == "qwen_tts"

    @patch.dict("os.environ", {"QWEN_API_KEY": "test"})
    def test_get_qwen_omni(self):
        container = Container.from_env()
        engine = container.get_tts_engine("qwen_omni")
        assert engine.get_engine_name() == "qwen_omni"

    @patch.dict("os.environ", {"MINIMAX_API_KEY": "test"})
    def test_engine_cache(self):
        container = Container.from_env()
        e1 = container.get_tts_engine("minimax")
        e2 = container.get_tts_engine("minimax")
        assert e1 is e2

    @patch.dict("os.environ", {"MINIMAX_API_KEY": "test", "QWEN_API_KEY": "test"})
    def test_synthesize_use_case(self):
        container = Container.from_env()
        uc = container.synthesize_use_case("minimax")
        assert uc.engine is not None

    @patch.dict("os.environ", {"MINIMAX_API_KEY": "test", "QWEN_API_KEY": "test"})
    def test_fallback_tts(self):
        container = Container.from_env()
        fallback = container.get_fallback_tts("minimax")
        assert fallback is not None
        assert fallback.get_engine_name() == "qwen_tts"

    def test_missing_api_key(self):
        import os
        container = Container.from_env()
        # 临时清除环境变量
        saved = os.environ.pop("MINIMAX_API_KEY", None)
        try:
            import pytest
            with pytest.raises(ValueError, match="MINIMAX_API_KEY"):
                container.get_tts_engine("minimax")
        finally:
            if saved:
                os.environ["MINIMAX_API_KEY"] = saved
