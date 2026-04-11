def split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """
    Divide un texto en fragmentos con solapamiento.
    """
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += max(chunk_size - overlap, 1)

    return chunks