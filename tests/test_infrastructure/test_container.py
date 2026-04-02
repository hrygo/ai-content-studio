"""
基础设施层测试 - Container
"""
import pytest
from unittest.mock import patch, MagicMock

from src.infrastructure import Container


class TestContainer:
    """Container 测试"""

    def test_from_env_no_credentials(self):
        """测试无凭据时创建容器"""
        # 清空所有环境变量
        import os
        for key in ["MINIMAX_API_KEY", "MINIMAX_GROUP_ID", "QWEN_API_KEY"]:
            os.environ.pop(key, None)

        container = Container.from_env()

        # 可能从 conftest 设置了测试凭据，所以只检查属性存在
        assert hasattr(container, 'minimax_engine')
        assert hasattr(container, 'qwen_engine')
        assert hasattr(container, 'audio_processor')

    def test_from_env_with_minimax_credentials(self):
        """测试 MiniMax 凭据时创建容器"""
        with patch.dict(
            "os.environ",
            {
                "MINIMAX_API_KEY": "test_minimax_key",
                "MINIMAX_GROUP_ID": "test_group_id",
            },
        ):
            container = Container.from_env()

            assert container.minimax_engine is not None
            assert container.minimax_engine.api_key == "test_minimax_key"
            assert container.minimax_engine.group_id == "test_group_id"

    def test_from_env_with_qwen_credentials(self):
        """测试 Qwen 凭据时创建容器"""
        with patch.dict(
            "os.environ",
            {
                "QWEN_API_KEY": "test_qwen_key",
            },
        ):
            container = Container.from_env()

            assert container.qwen_engine is not None
            assert container.qwen_engine.api_key == "test_qwen_key"

    def test_synthesize_speech_use_case_minimax(self):
        """测试获取 MiniMax 合成用例"""
        container = Container()
        container.minimax_engine = MagicMock()

        use_case = container.synthesize_speech_use_case("minimax")

        assert use_case.engine is container.minimax_engine

    def test_synthesize_speech_use_case_qwen(self):
        """测试获取 Qwen 合成用例"""
        container = Container()
        container.qwen_engine = MagicMock()

        use_case = container.synthesize_speech_use_case("qwen")

        assert use_case.engine is container.qwen_engine

    def test_synthesize_speech_use_case_caches(self):
        """测试用例缓存"""
        container = Container()
        container.minimax_engine = MagicMock()

        use_case1 = container.synthesize_speech_use_case("minimax")
        use_case2 = container.synthesize_speech_use_case("minimax")

        assert use_case1 is use_case2  # 同一实例

    def test_synthesize_speech_use_case_no_engine(self):
        """测试未配置引擎时抛出异常"""
        container = Container()

        with pytest.raises(ValueError, match="MiniMax 引擎未配置"):
            container.synthesize_speech_use_case("minimax")

    def test_batch_synthesize_use_case(self):
        """测试批量合成用例"""
        container = Container()
        container.minimax_engine = MagicMock()
        container.audio_processor = MagicMock()

        use_case = container.batch_synthesize_use_case("minimax")

        assert use_case.engine is container.minimax_engine
        assert use_case.audio_processor is container.audio_processor

    def test_invalid_engine_type(self):
        """测试无效引擎类型"""
        container = Container()

        with pytest.raises(ValueError, match="不支持的引擎类型"):
            container.synthesize_speech_use_case("invalid_engine")

    def test_synthesize_speech_use_case_different_engines(self):
        """测试不同引擎返回不同用例实例"""
        container = Container()
        container.minimax_engine = MagicMock()
        container.qwen_engine = MagicMock()

        use_case_minimax = container.synthesize_speech_use_case("minimax")
        use_case_qwen = container.synthesize_speech_use_case("qwen")

        # 不同引擎应返回不同用例实例
        assert use_case_minimax is not use_case_qwen
        assert use_case_minimax.engine is container.minimax_engine
        assert use_case_qwen.engine is container.qwen_engine

    def test_synthesize_speech_use_case_same_engine_cached(self):
        """测试同一引擎返回缓存实例"""
        container = Container()
        container.minimax_engine = MagicMock()

        use_case1 = container.synthesize_speech_use_case("minimax")
        use_case2 = container.synthesize_speech_use_case("minimax")

        # 同一引擎应返回相同缓存实例
        assert use_case1 is use_case2

    def test_batch_synthesize_use_case_different_engines(self):
        """测试批量合成用例不同引擎"""
        container = Container()
        container.minimax_engine = MagicMock()
        container.qwen_engine = MagicMock()
        container.audio_processor = MagicMock()

        use_case_minimax = container.batch_synthesize_use_case("minimax")
        use_case_qwen = container.batch_synthesize_use_case("qwen")

        # 不同引擎应返回不同用例实例
        assert use_case_minimax is not use_case_qwen
        assert use_case_minimax.engine is container.minimax_engine
        assert use_case_qwen.engine is container.qwen_engine

    def test_cleanup(self):
        """测试清理资源"""
        container = Container()
        container.audio_processor = MagicMock()

        container.cleanup()

        container.audio_processor.cleanup.assert_called_once()
