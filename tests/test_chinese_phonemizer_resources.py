"""Tests for Chinese phonemizer resource management."""

import sys
import types
from io import BytesIO

from piper import phonemize_chinese


class FakeResponse(BytesIO):
    """Bytes response compatible with urllib response context management."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def test_download_bert_base_chinese_tokenizer_downloads_missing_files(
    tmp_path, monkeypatch
) -> None:
    """Test that missing tokenizer files are downloaded into the local model dir."""

    requested_urls: list[str] = []

    def fake_urlopen(url: str) -> FakeResponse:
        requested_urls.append(url)
        return FakeResponse(f"contents for {url}".encode("utf-8"))

    monkeypatch.setattr(phonemize_chinese, "urlopen", fake_urlopen)

    tokenizer_dir = tmp_path / "g2pW" / "bert-base-chinese"
    phonemize_chinese.download_bert_base_chinese_tokenizer(tokenizer_dir)

    assert len(requested_urls) == len(
        phonemize_chinese.BERT_BASE_CHINESE_TOKENIZER_FILES
    )
    for file_name in phonemize_chinese.BERT_BASE_CHINESE_TOKENIZER_FILES:
        assert (tokenizer_dir / file_name).exists()


def test_download_bert_base_chinese_tokenizer_skips_existing_files(
    tmp_path, monkeypatch
) -> None:
    """Test that cached tokenizer files do not trigger network requests."""

    tokenizer_dir = tmp_path / "bert-base-chinese"
    tokenizer_dir.mkdir()
    for file_name in phonemize_chinese.BERT_BASE_CHINESE_TOKENIZER_FILES:
        (tokenizer_dir / file_name).write_text("cached", encoding="utf-8")

    def fail_urlopen(url: str) -> FakeResponse:
        raise AssertionError(f"unexpected download: {url}")

    monkeypatch.setattr(phonemize_chinese, "urlopen", fail_urlopen)

    phonemize_chinese.download_bert_base_chinese_tokenizer(tokenizer_dir)


def test_download_bert_base_chinese_tokenizer_does_not_require_optional_files(
    tmp_path, monkeypatch
) -> None:
    """Test that absent optional tokenizer files do not trigger downloads."""

    tokenizer_dir = tmp_path / "bert-base-chinese"
    tokenizer_dir.mkdir()
    for file_name in phonemize_chinese.BERT_BASE_CHINESE_TOKENIZER_FILES:
        (tokenizer_dir / file_name).write_text("cached", encoding="utf-8")

    def fail_urlopen(url: str) -> FakeResponse:
        raise AssertionError(f"unexpected download: {url}")

    monkeypatch.setattr(phonemize_chinese, "urlopen", fail_urlopen)

    phonemize_chinese.download_bert_base_chinese_tokenizer(tokenizer_dir)
    assert not (tokenizer_dir / "special_tokens_map.json").exists()


def test_chinese_phonemizer_uses_local_bert_tokenizer(tmp_path, monkeypatch) -> None:
    """Test that g2pW is pointed at Piper's local tokenizer resource."""

    captured_kwargs = {}

    class FakeG2PWConverter:
        def __init__(self, **kwargs) -> None:
            captured_kwargs.update(kwargs)

    class FakeRbnfEngine:
        @staticmethod
        def for_language(language: str) -> object:
            return object()

    fake_g2pw = types.ModuleType("g2pw")
    fake_g2pw.G2PWConverter = FakeG2PWConverter
    fake_unicode_rbnf = types.ModuleType("unicode_rbnf")
    fake_unicode_rbnf.RbnfEngine = FakeRbnfEngine

    monkeypatch.setitem(sys.modules, "g2pw", fake_g2pw)
    monkeypatch.setitem(sys.modules, "unicode_rbnf", fake_unicode_rbnf)
    monkeypatch.setattr(phonemize_chinese, "download_model", lambda model_dir: None)

    model_dir = tmp_path / "g2pW"
    phonemize_chinese.ChinesePhonemizer(model_dir)

    assert captured_kwargs["model_source"] == str(model_dir / "bert-base-chinese")
