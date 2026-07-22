"""
Text chunking utility.

A small, dependency-free sliding-window chunker. Kept out of
vector_store_service so it can be unit tested in isolation and reused by
any future ingestion path (e.g. streaming ingestion) without pulling in
Chroma or Gemini imports.
"""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """
    Split text into overlapping chunks suitable for embedding.

    Overlap preserves context across chunk boundaries so a fact split across
    two chunks (e.g. "...inspection every 6 months" / "for all class-A
    valves...") is still retrievable from either chunk.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")

    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_len:
            break
        start = end - overlap

    return chunks
