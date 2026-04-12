"""Use Cases 测试"""
from pathlib import Path
from unittest.mock import Mock, patch

from voiceforge.entities import EngineResult, TTSRequest, VoiceConfig, AudioSegment
from voiceforge.use_cases.synthesize import SynthesizeSpeechUseCase, BatchSynthesizeUseCase
from voiceforge.use_cases.dialogue import (
    DialogueSpeechUseCase, parse_dialogue_segments, VoiceAllocator, compute_pan_values,
)
from voiceforge.use_cases.podcast import StudioPodcastUseCase


class TestSynthesizeUseCase:
    def test_success(self, mock_tts_engine):
        uc = SynthesizeSpeechUseCase(engine=mock_tts_engine)
        result = uc.execute(text="hello", output_file=Path("out.mp3"))
        assert result.success
        mock_tts_engine.synthesize.assert_called_once()

    def test_empty_text(self, mock_tts_engine):
        uc = SynthesizeSpeechUseCase(engine=mock_tts_engine)
        result = uc.execute(text="", output_file=Path("out.mp3"))
        assert not result.success


class TestBatchUseCase:
    def test_single_segment(self, mock_tts_engine, mock_audio_processor):
        uc = BatchSynthesizeUseCase(engine=mock_tts_engine, audio_processor=mock_audio_processor)
        segments = [AudioSegment(text="hello", voice_id="cherry")]
        result = uc.execute(segments, Path("out.mp3"))
        assert result.success

    def test_empty_segments(self, mock_tts_engine, mock_audio_processor):
        uc = BatchSynthesizeUseCase(engine=mock_tts_engine, audio_processor=mock_audio_processor)
        result = uc.execute([], Path("out.mp3"))
        assert not result.success

    def test_fallback(self, mock_audio_processor):
        failing = Mock()
        failing.synthesize.return_value = EngineResult.fail("1008 insufficient balance")

        fallback = Mock()
        fallback.synthesize.return_value = EngineResult.ok(Path("out.mp3"), 5.0, "fallback")
        fallback.get_engine_name.return_value = "fallback"

        uc = BatchSynthesizeUseCase(
            engine=failing, audio_processor=mock_audio_processor, fallback_engine=fallback,
        )
        segments = [AudioSegment(text="hello")]
        result = uc.execute(segments, Path("out.mp3"))
        assert result.success
        fallback.synthesize.assert_called_once()


class TestParseDialogue:
    def test_basic(self):
        text = "[Alex]: 你好\n[Sam]: 你好 Alex"
        result = parse_dialogue_segments(text)
        assert len(result) == 2
        assert result[0][0].text == "你好"
        assert result[0][0].voice_id == "Alex"
        assert result[1][0].voice_id == "Sam"

    def test_with_emotion(self):
        text = "[Alex, happy]: 太好了！"
        result = parse_dialogue_segments(text)
        assert len(result) == 1
        assert result[0][1] == "happy"

    def test_empty(self):
        assert parse_dialogue_segments("") == []


class TestVoiceAllocator:
    def test_round_robin(self):
        alloc = VoiceAllocator()
        v1 = alloc.get_voice("A")
        v2 = alloc.get_voice("B")
        v3 = alloc.get_voice("C")
        assert v1 != v2 != v3

    def test_config_mapping(self):
        alloc = VoiceAllocator({"Alex": {"voice": "cherry"}, "Sam": "ethan"})
        assert alloc.get_voice("Alex") == "cherry"
        assert alloc.get_voice("Sam") == "ethan"

    def test_case_insensitive(self):
        alloc = VoiceAllocator({"alex": {"voice": "cherry"}})
        assert alloc.get_voice("ALEX") == "cherry"


class TestPanValues:
    def test_single_role(self):
        assert compute_pan_values(["Alex"]) == {"Alex": 0.0}

    def test_two_roles(self):
        pan = compute_pan_values(["Alex", "Sam"])
        assert pan["Alex"] == -0.8
        assert pan["Sam"] == 0.8


class TestDialogueUseCase:
    def test_basic(self, mock_tts_engine, mock_audio_processor):
        uc = DialogueSpeechUseCase(engine=mock_tts_engine, audio_processor=mock_audio_processor)
        result = uc.execute("[Alex]: 你好\n[Sam]: 你好 Alex", Path("out.mp3"))
        assert result.success

    def test_empty_script(self, mock_tts_engine, mock_audio_processor):
        uc = DialogueSpeechUseCase(engine=mock_tts_engine, audio_processor=mock_audio_processor)
        result = uc.execute("", Path("out.mp3"))
        assert not result.success


class TestPodcastUseCase:
    def test_basic(self, mock_tts_engine, mock_llm_engine, mock_audio_processor):
        uc = StudioPodcastUseCase(
            llm_engine=mock_llm_engine,
            tts_engine=mock_tts_engine,
            audio_processor=mock_audio_processor,
        )
        result = uc.execute(topic="AI", output_file=Path("podcast.mp3"))
        assert result.success

    def test_llm_unavailable(self, mock_tts_engine, mock_audio_processor):
        mock_llm = Mock()
        mock_llm.is_available.return_value = False
        uc = StudioPodcastUseCase(
            llm_engine=mock_llm, tts_engine=mock_tts_engine,
            audio_processor=mock_audio_processor,
        )
        result = uc.execute(topic="AI", output_file=Path("podcast.mp3"))
        assert not result.success
