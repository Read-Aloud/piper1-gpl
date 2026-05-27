"""Piper text-to-speech engine."""

from .config import PhonemeType, PiperConfig, SynthesisConfig

__all__ = [
    "AudioChunk",
    "PhonemeType",
    "PiperConfig",
    "PiperVoice",
    "SynthesisConfig",
]


def __getattr__(name: str):
    """Lazily import synthesis classes."""

    if name in {"AudioChunk", "PiperVoice"}:
        from .voice import AudioChunk, PiperVoice

        return {
            "AudioChunk": AudioChunk,
            "PiperVoice": PiperVoice,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
