import re


def split_by_articles(text: str) -> list[dict]:
    """
    Intenta dividir el texto por artículos.
    Devuelve bloques con metadatos básicos.
    """
    pattern = r"(?=(Artículo\s+\d+\.?))"
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))

    if len(matches) < 2:
        return []

    chunks = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()

        article_match = re.search(r"Artículo\s+(\d+)", block, flags=re.IGNORECASE)
        article_number = article_match.group(1) if article_match else None

        if block:
            chunks.append({
                "text": block,
                "strategy": "article",
                "article_number": article_number,
                "section_title": None
            })

    return chunks


def split_by_sections(text: str) -> list[dict]:
    """
    Intenta dividir por encabezados o secciones tipo CAPÍTULO, REQUISITOS, etc.
    """
    pattern = r"(?=(CAPÍTULO\s+[IVXLC]+|REQUISITOS|PROCEDIMIENTO|OBSERVACIONES|PLAZOS|DOCUMENTOS A PRESENTAR))"
    matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))

    if len(matches) < 2:
        return []

    chunks = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()

        title_match = re.search(
            r"(CAPÍTULO\s+[IVXLC]+|REQUISITOS|PROCEDIMIENTO|OBSERVACIONES|PLAZOS|DOCUMENTOS A PRESENTAR)",
            block,
            flags=re.IGNORECASE
        )
        section_title = title_match.group(1) if title_match else None

        if block:
            chunks.append({
                "text": block,
                "strategy": "section",
                "article_number": None,
                "section_title": section_title
            })

    return chunks


def split_by_paragraphs(text: str, max_chars: int = 1200) -> list[dict]:
    """
    Divide por párrafos y agrupa párrafos hasta un tamaño razonable.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    if not paragraphs:
        return []

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append({
                    "text": current,
                    "strategy": "paragraph",
                    "article_number": None,
                    "section_title": None
                })
            current = paragraph

    if current:
        chunks.append({
            "text": current,
            "strategy": "paragraph",
            "article_number": None,
            "section_title": None
        })

    return chunks


def split_by_characters(text: str, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """
    Último recurso: división por caracteres con overlap.
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
            chunks.append({
                "text": chunk,
                "strategy": "character",
                "article_number": None,
                "section_title": None
            })

        start += max(chunk_size - overlap, 1)

    return chunks


def split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """
    Estrategia híbrida:
    1. artículos
    2. secciones
    3. párrafos
    4. caracteres
    """
    if not text.strip():
        return []

    article_chunks = split_by_articles(text)
    if article_chunks:
        return article_chunks

    section_chunks = split_by_sections(text)
    if section_chunks:
        return section_chunks

    paragraph_chunks = split_by_paragraphs(text)
    if paragraph_chunks:
        return paragraph_chunks

    return split_by_characters(text, chunk_size=chunk_size, overlap=overlap)