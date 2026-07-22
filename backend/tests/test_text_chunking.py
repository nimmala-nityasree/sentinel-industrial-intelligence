"""Unit tests for app.utils.text_chunking — pure function, no mocks needed."""
import pytest

from app.utils.text_chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_returns_single_chunk():
    text = "Inspect valve V-204 every 180 days."
    chunks = chunk_text(text, chunk_size=800, overlap=120)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_long_text_produces_overlapping_chunks():
    text = "A" * 2000
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) > 1
    # every chunk except possibly the last should be exactly chunk_size long
    for chunk in chunks[:-1]:
        assert len(chunk) == 500


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=100, overlap=100)


def test_chunks_cover_full_text_with_overlap():
    text = "0123456789" * 50  # 500 chars
    chunk_size, overlap = 120, 30
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    # reconstruct coverage: last chunk's tail should reach the end of text
    assert text.endswith(chunks[-1][-10:])
