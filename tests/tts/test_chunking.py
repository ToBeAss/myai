"""Tests for TTS chunk-boundary heuristics."""

import importlib
import sys
from pathlib import Path

# Import the chunking module directly to avoid pulling in google.cloud
# via myai.tts.__init__.py (which imports TextToSpeech).
_chunking_path = Path(__file__).resolve().parents[2] / "src" / "myai" / "tts" / "chunking.py"
_spec = importlib.util.spec_from_file_location("myai.tts.chunking", _chunking_path)
_mod = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("myai.tts.chunking", _mod)
_spec.loader.exec_module(_mod)
find_sentence_boundary = _mod.find_sentence_boundary


class TestFindSentenceBoundary:
    """Regression tests for find_sentence_boundary (last vs first_only)."""

    def test_last_boundary_default(self):
        text = "Hello world. Another sentence!"
        assert find_sentence_boundary(text) == 29

    def test_first_only_boundary(self):
        text = "Hello world. Another sentence!"
        assert find_sentence_boundary(text, first_only=True) == 11

    def test_decimal_not_split(self):
        assert find_sentence_boundary("The value is 3.14 and rising.") == 28

    def test_decimal_only_no_boundary(self):
        assert find_sentence_boundary("Version 2.0") == -1

    def test_initials_stay_connected(self):
        assert find_sentence_boundary("Meet J. T. Smith.") == 16

    def test_initials_first_only(self):
        assert find_sentence_boundary("Meet J. T. Smith.", first_only=True) == 16

    def test_weak_commas_skipped(self):
        assert find_sentence_boundary("Count 1, 2, 3", chunk_chars=",") == -1

    def test_no_boundary_returns_negative(self):
        assert find_sentence_boundary("no punctuation here") == -1

    def test_empty_string(self):
        assert find_sentence_boundary("") == -1

    def test_first_only_with_commas(self):
        text = "Alpha, beta gamma delta epsilon zeta, final stop."
        # First strong comma is at index 36 ("zeta,")
        idx = find_sentence_boundary(text, chunk_chars=",.!?", first_only=True)
        assert idx == 36

    def test_last_with_commas(self):
        text = "Alpha, beta gamma delta epsilon zeta, final stop."
        # Last boundary is the period at index 48
        idx = find_sentence_boundary(text, chunk_chars=",.!?")
        assert idx == 48
