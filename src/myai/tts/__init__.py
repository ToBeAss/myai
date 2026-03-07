"""Text-to-speech package."""

from .chunking import find_sentence_boundary, is_sentence_boundary, is_weak_comma
from .text_to_speech import TextToSpeech

__all__ = [
	"TextToSpeech",
	"find_sentence_boundary",
	"is_sentence_boundary",
	"is_weak_comma",
]
