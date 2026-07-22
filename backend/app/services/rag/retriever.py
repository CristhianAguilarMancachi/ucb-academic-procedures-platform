import re
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer

from app.core.config import EMBEDDING_MODEL, TOP_K
from app.repositories.chunk_repository import search_similar_chunks

embedding_model = SentenceTransformer(EMBEDDING_MODEL)


STOPWORDS = {
    "qué", "que", "cuál", "cual", "cuántas", "cuantas", "cuántos", "cuantos",
    "de", "la", "el", "los", "las", "un", "una", "y", "o", "a", "en", "por",
    "para", "si", "se", "es", "del", "al"
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑ]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def score_chunk(chunk, query_terms: set[str]) -> float:
    content = chunk.contenido or ""
    subsection = chunk.subseccion or ""

    content_terms = tokenize(content)
    subsection_terms = tokenize(subsection)

    overlap_content = len(query_terms & content_terms)
    overlap_subsection = len(query_terms & subsection_terms)

    score = 0.0

    # bonificar coincidencias semánticas simples
    score += overlap_content * 2.0
    score += overlap_subsection * 3.0

    # penalizar chunks muy cortos
    word_count = len(content.split())
    if word_count < 25:
        score -= 3.0
    elif word_count < 50:
        score -= 1.5

    # penalizar subsecciones demasiado genéricas
    generic_subsections = {
        "", "parte 1", "parte 2", "parte 3",
        "capitulo i", "capitulo ii", "capitulo iii", "capitulo iv"
    }
    if subsection.strip().lower() in generic_subsections:
        score -= 1.5

    # bonificar chunks de tamaño razonable
    if 50 <= word_count <= 220:
        score += 1.0

    return score


def retrieve_relevant_chunks(
    db: Session,
    query: str,
    top_k: int | None = None,
    allowed_documents: list[str] | None = None
):
    effective_top_k = top_k or TOP_K

    query_embedding = embedding_model.encode(query).tolist()

    # recupera más candidatos para reordenar mejor
    candidate_chunks = search_similar_chunks(
        db=db,
        query_embedding=query_embedding,
        top_k=max(effective_top_k * 3, 10),
        allowed_documents=allowed_documents
    )

    query_terms = tokenize(query)

    ranked_chunks = sorted(
        candidate_chunks,
        key=lambda chunk: score_chunk(chunk, query_terms),
        reverse=True
    )

    final_chunks = ranked_chunks[:effective_top_k]

    documents = [chunk.contenido for chunk in final_chunks]
    metadatas = [
        {
            "document": (
                chunk.version_documento.documento.titulo
                if chunk.version_documento and chunk.version_documento.documento
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