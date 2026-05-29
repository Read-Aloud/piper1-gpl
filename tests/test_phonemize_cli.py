"""Tests for the phonemization CLI helpers."""

from piper.phonemize import get_request, phonemize_request, process_line


class FakeEspeakPhonemizer:
    """Test double for eSpeak phonemization."""

    def phonemize(self, voice: str, text: str) -> list[list[str]]:
        """Return the call arguments as phoneme-like data."""

        if voice == "bad":
            raise RuntimeError("Failed to set voice: bad")

        return [[voice, text]]


class FakeChinesePhonemizer:
    """Test double for Chinese pinyin phonemization."""

    def phonemize(self, text: str) -> list[list[str]]:
        """Return pinyin-like data."""

        return [[text, "pinyin"]]


class FakeTashkeelDiacritizer:
    """Test double for Arabic diacritization."""

    def diacritize(self, text: str, taskeen_threshold=None) -> str:
        """Return diacritized-like data."""

        return f"{text}|tashkeel={taskeen_threshold}"


class FakePhonemizers:
    """Test double for lazy phonemizer holder."""

    espeak = FakeEspeakPhonemizer()
    chinese = FakeChinesePhonemizer()
    tashkeel = FakeTashkeelDiacritizer()


def test_get_request() -> None:
    """Test JSONL phonemize requests."""

    assert get_request("\n") is None
    assert get_request(
        '{"phonemeType": "espeak", "voice": "en-us", "text": "Test 1."}\n'
    ) == {
        "phonemeType": "espeak",
        "voice": "en-us",
        "text": "Test 1.",
    }
    assert get_request('{"phonemeType": "text", "text": "abc"}\n') == {
        "phonemeType": "text",
        "text": "abc",
    }
    assert get_request(
        (
            '{"phonemeType": "espeak", "voice": "ar", "text": "مرحبا", '
            '"useTashkeel": false, "taskeenThreshold": 0.5}\n'
        )
    ) == {
        "phonemeType": "espeak",
        "voice": "ar",
        "text": "مرحبا",
        "useTashkeel": False,
        "taskeenThreshold": 0.5,
    }


def test_phonemize_request_espeak() -> None:
    """Test direct eSpeak phonemizer calls."""

    result = phonemize_request(
        FakePhonemizers(),  # type: ignore[arg-type]
        {"phonemeType": "espeak", "voice": "en-us", "text": "Test 1."},
    )

    assert result == {
        "text": "Test 1.",
        "phonemeType": "espeak",
        "phonemes": [["en-us", "Test 1."]],
    }


def test_phonemize_request_espeak_arabic_diacritizes() -> None:
    """Test that Arabic eSpeak requests are diacritized by default."""

    result = phonemize_request(
        FakePhonemizers(),  # type: ignore[arg-type]
        {"phonemeType": "espeak", "voice": "ar", "text": "مرحبا"},
    )

    assert result == {
        "text": "مرحبا",
        "phonemeType": "espeak",
        "phonemes": [["ar", "مرحبا|tashkeel=0.8"]],
    }


def test_phonemize_request_espeak_arabic_can_disable_diacritization() -> None:
    """Test that Arabic diacritization can be disabled per request."""

    result = phonemize_request(
        FakePhonemizers(),  # type: ignore[arg-type]
        {
            "phonemeType": "espeak",
            "voice": "ar",
            "text": "مرحبا",
            "useTashkeel": False,
        },
    )

    assert result == {
        "text": "مرحبا",
        "phonemeType": "espeak",
        "phonemes": [["ar", "مرحبا"]],
    }


def test_phonemize_request_espeak_arabic_taskeen_threshold() -> None:
    """Test that Arabic diacritization accepts a taskeen threshold."""

    result = phonemize_request(
        FakePhonemizers(),  # type: ignore[arg-type]
        {
            "phonemeType": "espeak",
            "voice": "ar",
            "text": "مرحبا",
            "taskeenThreshold": 0.5,
        },
    )

    assert result == {
        "text": "مرحبا",
        "phonemeType": "espeak",
        "phonemes": [["ar", "مرحبا|tashkeel=0.5"]],
    }


def test_phonemize_request_text() -> None:
    """Test text phonemization."""

    result = phonemize_request(
        FakePhonemizers(),  # type: ignore[arg-type]
        {"phonemeType": "text", "text": "cafe"},
    )

    assert result == {
        "text": "cafe",
        "phonemeType": "text",
        "phonemes": [["c", "a", "f", "e"]],
    }


def test_phonemize_request_pinyin() -> None:
    """Test pinyin phonemization dispatch."""

    result = phonemize_request(
        FakePhonemizers(),  # type: ignore[arg-type]
        {"phonemeType": "pinyin", "text": "ni hao"},
    )

    assert result == {
        "text": "ni hao",
        "phonemeType": "pinyin",
        "phonemes": [["ni hao", "pinyin"]],
    }


def test_process_line_returns_error_response() -> None:
    """Test that runtime errors become JSON responses."""

    result = process_line(
        FakePhonemizers(),  # type: ignore[arg-type]
        '{"phonemeType": "espeak", "voice": "bad", "text": "Test"}',
    )

    assert result == {
        "error": "RuntimeError",
        "message": "Failed to set voice: bad",
    }
