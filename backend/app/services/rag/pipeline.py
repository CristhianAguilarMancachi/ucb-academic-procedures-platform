from app.services.rag.retriever import retrieve_relevant_chunks
from app.services.rag.prompt_builder import build_rag_prompt
from app.services.rag.generator import generate_response
from app.services.rag.tramites_catalog import get_tramite_by_id


def score_chunk(question: str, chunk_text: str, metadata: dict) -> int:
    score = 0

    question_lower = question.lower()
    chunk_lower = chunk_text.lower()

    question_words = [
        word.strip("¿?.,:;()[]{}\"'").lower()
        for word in question.split()
        if len(word.strip("¿?.,:;()[]{}\"'")) > 3
    ]

    for word in question_words:
        if word in chunk_lower:
            score += 2

    if "requisito" in question_lower or "requisitos" in question_lower:
        if "requisito" in chunk_lower or "requisitos" in chunk_lower:
            score += 4

    if "diploma académico" in question_lower and "diploma académico" in chunk_lower:
        score += 6

    if "título profesional" in question_lower and "título profesional" in chunk_lower:
        score += 6

    if "revalidación" in question_lower and "revalidación" in chunk_lower:
        score += 6

    if metadata.get("article_number"):
        score += 1

    if metadata.get("chunk_strategy") == "article":
        score += 1

    return score


def select_best_chunks(
    question: str,
    documents: list[str],
    metadatas: list[dict],
    max_chunks: int = 3
) -> tuple[list[str], list[dict]]:
    paired = list(zip(documents, metadatas))

    scored = []
    for doc, meta in paired:
        scored.append((score_chunk(question, doc, meta), doc, meta))

    scored.sort(key=lambda item: item[0], reverse=True)

    selected = scored[:max_chunks]

    selected_documents = [item[1] for item in selected]
    selected_metadatas = [item[2] for item in selected]

    return selected_documents, selected_metadatas


def run_rag_pipeline(question: str, selected_tramite: str | None = None) -> dict:
    allowed_documents = None

    if selected_tramite:
        tramite = get_tramite_by_id(selected_tramite)
        if tramite:
            allowed_documents = tramite["document_names"]

    retrieved_documents, retrieved_metadatas = retrieve_relevant_chunks(
        query=question,
        top_k=4,
        allowed_documents=allowed_documents
    )

    if not retrieved_documents:
        return {
            "question": question,
            "answer": "No se encontró información relevante para responder la consulta.",
            "sources": [],
            "selected_tramite": selected_tramite,
        }

    selected_documents, selected_metadatas = select_best_chunks(
        question=question,
        documents=retrieved_documents,
        metadatas=retrieved_metadatas,
        max_chunks=3
    )

    prompt = build_rag_prompt(question, selected_documents, selected_metadatas)
    answer = generate_response(prompt)

    sources = []
    seen = set()

    for meta in selected_metadatas:
        source_key = (
            meta.get("source"),
            meta.get("page"),
            meta.get("article_number"),
            meta.get("chunk_strategy"),
        )

        if source_key in seen:
            continue
        seen.add(source_key)

        sources.append({
            "document": meta.get("source"),
            "page": meta.get("page"),
            "article_number": meta.get("article_number"),
            "chunk_strategy": meta.get("chunk_strategy"),
        })

    return {
        "question": question,
        "answer": answer,
        "sources": sources,
        "selected_tramite": selected_tramite,
    }