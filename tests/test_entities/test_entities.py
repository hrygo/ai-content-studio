"""实体层测试"""
from pathlib import Path
from voiceforge.entities import (
    AudioSegment, EngineResult, TTSRequest, VoiceConfig,
    ErrorType, TTSEngineType, EmotionType, QwenVoiceID, LanguageCode,
)


class TestAudioSegment:
    def test_default_voice(self):
        seg = AudioSegment(text="hello")
        assert seg.voice_id == "male-qn-qingse"

    def test_custom_voice(self):
        seg = AudioSegment(text="hello", voice_id="cherry")
        assert seg.voice_id == "cherry"

    def test_frozen(self):
        seg = AudioSegment(text="hello")
        try:
            seg.text = "changed"
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestEngineResult:
    def test_success(self):
        r = EngineResult.ok(Path("out.mp3"), 5.0, "minimax")
        assert r.success
        assert r.file_path == Path("out.mp3")
        assert r.duration == 5.0

    def test_failure(self):
        r = EngineResult.fail("error msg")
        assert not r.success
        assert r.error_message == "error msg"

    def test_default_values(self):
        r = EngineResult(success=False)
        assert r.file_path is None
        assert r.duration == 0.0


class TestTTSRequest:
    def test_properties(self):
        req = TTSRequest(
            text="hello",
            output_file=Path("out.mp3"),
            voice_config=VoiceConfig(voice_id="cherry", speed=1.2, emotion="happy"),
        )
        assert req.voice_id == "cherry"
        assert req.speed == 1.2
        assert req.emotion == "happy"

    def test_default_properties(self):
        req = TTSRequest(text="hello", output_file=Path("out.mp3"))
        assert req.voice_id == "male-qn-qingse"
        assert req.speed == 1.0


class TestErrorType:
    def test_classify_retryable(self):
        assert ErrorType.classify("timeout error") == ErrorType.RETRYABLE
        assert ErrorType.classify("rate limit exceeded") == ErrorType.RETRYABLE
        assert ErrorType.classify("2056 usage limit") == ErrorType.RETRYABLE

    def test_classify_fallback(self):
        assert ErrorType.classify("1008 insufficient balance") == ErrorType.FALLBACK
        assert ErrorType.classify("voice not licensed") == ErrorType.FALLBACK
        assert ErrorType.classify("api error bad request") == ErrorType.FALLBACK

    def test_classify_fatal(self):
        assert ErrorType.classify("unknown issue") == ErrorType.FATAL
        assert ErrorType.classify(None) == ErrorType.FATAL


class TestEnums:
    def test_tts_engine_alias(self):
        assert TTSEngineType.from_string("qwen") == TTSEngineType.QWEN_TTS

    def test_emotion_from_string(self):
        assert EmotionType.from_string("HAPPY") == EmotionType.HAPPY
        assert EmotionType.from_string("  calm  ") == EmotionType.CALM
        assert EmotionType.from_string("unknown") == EmotionType.NEUTRAL

    def test_qwen_voice(self):
        assert QwenVoiceID.from_string("CHERRY") == QwenVoiceID.CHERRY
        assert QwenVoiceID.from_string("unknown") == QwenVoiceID.CHERRY

    def test_language_code(self):
        assert LanguageCode.from_string("zh") == LanguageCode.ZH
        assert LanguageCode.from_string("invalid") == LanguageCode.AUTO
