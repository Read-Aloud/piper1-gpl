"""Line-oriented phonemization CLI for Piper."""

import argparse
import json
import logging
import sys
import unicodedata
from pathlib import Path
from typing import Any, Optional

from .phonemize_espeak import ESPEAK_DATA_DIR, EspeakPhonemizer

_LOGGER = logging.getLogger(__name__)
_PHONEME_TYPES = {"espeak", "text", "pinyin"}


class Phonemizers:
    """Lazy-loaded phonemizers."""

    def __init__(
        self,
        espeak_data_dir: Path = ESPEAK_DATA_DIR,
        download_dir: Optional[Path] = None,
    ) -> None:
        self.espeak_data_dir = espeak_data_dir
        self.download_dir = download_dir or Path.cwd()
        self._espeak: Optional[EspeakPhonemizer] = None
        self._chinese: Optional[Any] = None

    @property
    def espeak(self) -> EspeakPhonemizer:
        """Get the eSpeak phonemizer."""

        if self._espeak is None:
            self._espeak = EspeakPhonemizer(self.espeak_data_dir)

        return self._espeak

    @property
    def chinese(self) -> Any:
        """Get the Chinese pinyin phonemizer."""

        if self._chinese is None:
            from .phonemize_chinese import ChinesePhonemizer

            self._chinese = ChinesePhonemizer(self.download_dir / "g2pW")

        return self._chinese


def get_request(line: str) -> Optional[dict[str, str]]:
    """Parse one JSONL phonemization request."""

    line = line.strip()
    if not line:
        return None

    request = json.loads(line)
    if not isinstance(request, dict):
        raise ValueError("Phonemize request must be a JSON object")

    text = request.get("text")
    if not isinstance(text, str):
        raise ValueError("Phonemize request is missing string field: text")

    phoneme_type = request.get("phonemeType")
    if not isinstance(phoneme_type, str):
        raise ValueError("Phonemize request is missing string field: phonemeType")

    if phoneme_type not in _PHONEME_TYPES:
        raise ValueError(f"Unexpected phonemeType: {phoneme_type}")

    parsed_request = {"text": text, "phonemeType": phoneme_type}
    if phoneme_type == "espeak":
        voice = request.get("voice")
        if not isinstance(voice, str):
            raise ValueError("eSpeak phonemize request is missing string field: voice")

        parsed_request["voice"] = voice

    return parsed_request


def phonemize_request(
    phonemizers: Phonemizers, request: dict[str, str]
) -> dict[str, Any]:
    """Phonemize one request."""

    phoneme_type = request["phonemeType"]
    text = request["text"]
    if phoneme_type == "espeak":
        phonemes = phonemizers.espeak.phonemize(request["voice"], text)
    elif phoneme_type == "text":
        phonemes = [list(unicodedata.normalize("NFD", text))]
    elif phoneme_type == "pinyin":
        phonemes = phonemizers.chinese.phonemize(text)
    else:
        raise ValueError(f"Unexpected phonemeType: {phoneme_type}")

    return {
        "text": text,
        "phonemeType": phoneme_type,
        "phonemes": phonemes,
    }


def error_response(error: Exception) -> dict[str, str]:
    """Create a JSON-serializable error response."""

    return {
        "error": type(error).__name__,
        "message": str(error),
    }


def process_line(
    phonemizers: Phonemizers, line: str, debug: bool = False
) -> Optional[dict[str, Any]]:
    """Process one input line into a response."""

    try:
        request = get_request(line)
        if request is None:
            return None

        return phonemize_request(phonemizers, request)
    except Exception as err:  # pylint: disable=broad-exception-caught
        if debug:
            _LOGGER.exception("Failed to phonemize request")
        else:
            _LOGGER.error("Failed to phonemize request: %s", err)

        return error_response(err)


def main() -> None:
    """Run the Piper phonemization CLI."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--espeak-data-dir",
        "--espeak_data_dir",
        default=str(ESPEAK_DATA_DIR),
        help="Path to espeak-ng data directory",
    )
    parser.add_argument(
        "--download-dir",
        "--download_dir",
        default=str(Path.cwd()),
        help="Path to downloaded resources for phonemizers (default: cwd)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG messages to console"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    _LOGGER.debug(args)

    phonemizers = Phonemizers(
        espeak_data_dir=Path(args.espeak_data_dir),
        download_dir=Path(args.download_dir),
    )

    for line in sys.stdin:
        response = process_line(phonemizers, line, debug=args.debug)
        if response is None:
            continue

        json.dump(response, sys.stdout, ensure_ascii=False, separators=(",", ":"))
        sys.stdout.write("\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
