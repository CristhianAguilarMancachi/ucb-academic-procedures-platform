import re

from sqlalchemy.orm import Session

from app.core.config import TOP_K
from app.repositories.chunk_repository import search_similar_chunks
from app.services.rag.embeddings import generate_embedding


STOPWORDS = {
    "qué",
    "que",
    "cuál",
    "cual",
    "cuántas",
    "cuantas",
    "cuántos",
    "cuantos",
    "de",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "y",
    "o",
    "a",
    "en",
    "por",
    "para",
    "si",
    "se",
    "es",
    "del",
    "al",
}


def tokenize(text: str) -> set[str]:
    words = re.findall(
        r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]+",
        text.lower(),
    )

    return {
        word
        for word in words
        if word not in STOPWORDS and len(word) > 2
    }


def score_chunk(
    chunk,
    query_terms: set[str],
    retrieval_hints: dict[str, list[str]] | None = None,
) -> float:
    content = chunk.contenido or ""
    subsection = chunk.subseccion or ""
    section = chunk.seccion or ""
    article_number = chunk.articulo_numero or ""

    content_terms = tokenize(content)
    subsection_terms = tokenize(subsection)
    section_terms = tokenize(section)

    overlap_content = len(query_terms & content_terms)
    overlap_subsection = len(query_terms & subsection_terms)
    overlap_section = len(query_terms & section_terms)

    score = 0.0

    score += overlap_content * 2.0
    score += overlap_subsection * 3.0
    score += overlap_section * 2.0

    word_count = len(content.split())

    if word_count < 25:
        score -= 3.0
    elif word_count < 50:
        score -= 1.5

    generic_subsections = {
        "",
        "parte 1",
        "parte 2",
        "parte 3",
        "capitulo i",
        "capitulo ii",
        "capitulo iii",
        "capitulo iv",
    }

    if subsection.strip().lower() in generic_subsections:
        score -= 1.5

    if 50 <= word_count <= 220:
        score += 1.0

    if retrieval_hints:
        keywords = retrieval_hints.get(
            "keywords",
            [],
        )

        section_boost_terms = retrieval_hints.get(
            "section_boost_terms",
            [],
        )

        negative_terms = retrieval_hints.get(
            "negative_terms",
            [],
        )

        lowered_content = content.lower()
        lowered_subsection = subsection.lower()
        lowered_section = section.lower()
        lowered_article_number = article_number.lower()

        for term in keywords:
            normalized_term = term.lower()

            if normalized_term in lowered_content:
                score += 1.5

            if normalized_term in lowered_subsection:
                score += 2.0

            if normalized_term in lowered_section:
                score += 1.5

        for term in section_boost_terms:
            normalized_term = term.lower()

            if normalized_term in lowered_subsection:
                score += 2.5

            if normalized_term in lowered_section:
                score += 2.0

            if normalized_term in lowered_article_number:
                score += 1.0

        for term in negative_terms:
            normalized_term = term.lower()

            if normalized_term in lowered_content:
                score -= 1.0

    return score


def retrieve_relevant_chunks(
    db: Session,
    query: str,
    top_k: int | None = None,
    allowed_documents: list[str] | None = None,
    query_type: str | None = None,
    retrieval_hints: dict[str, list[str]] | None = None,
):
    if not query or not query.strip():
        return [], []

    effective_top_k = top_k or TOP_K

    query_embedding = generate_embedding(query)

    candidate_chunks = search_similar_chunks(
        db=db,
        query_embedding=query_embedding,
        top_k=max(effective_top_k * 3, 10),
        allowed_documents=allowed_documents,
    )

    query_terms = tokenize(query)

    ranked_chunks = sorted(
        candidate_chunks,
        key=lambda chunk: score_chunk(
            chunk,
            query_terms,
            retrieval_hints,
        ),
        reverse=True,
    )

    final_chunks = ranked_chunks[:effective_top_k]

    documents = [
        chunk.contenido
        for chunk in final_chunks
    ]

    metadatas = [
        {
            "document": (
                chunk.version_documento.documento.titulo
                if (
                    chunk.version_documento
                    and chunk.version_documento.documento
                )
                else None
            ),
            "page": chunk.pagina_inicio,
            "article_number": chunk.articulo_numero,
            "chunk_strategy": chunk.estrategia_chunking,
            "section": chunk.seccion,
            "subsection": chunk.subseccion,
        }
        for chunk in final_chunks
    ]

    return documents, metadatas