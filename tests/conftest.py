"""Pytest 配置"""
import os
import pytest
from pathlib import Path
from unittest.mock import Mock

# 测试环境变量
os.environ["MINIMAX_API_KEY"] = "test_key"
os.environ["MINIMAX_GROUP_ID"] = "test_group"
os.environ["QWEN_API_KEY"] = "test_qwen_key"


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def mock_tts_engine():
    engine = Mock()
    engine.synthesize.return_value = Mock(
        success=True, file_path=Path("out.mp3"), duration=5.0, engine_name="mock",
    )
    engine.get_engine_name.return_value = "mock"
    return engine


@pytest.fixture
def mock_llm_engine():
    engine = Mock()
    engine.generate.return_value = "[Alex]: 你好\n[Sam]: 你好 Alex"
    engine.is_available.return_value = True
    return engine


@pytest.fixture
def mock_audio_processor():
    processor = Mock()
    processor.merge_audio_files.return_value = Mock(
        success=True, file_path=Path("merged.mp3"), duration=10.0, engine_name="ffmpeg",
    )
    return processor
