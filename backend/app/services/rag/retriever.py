from app.services.rag.vector_store import get_or_create_collection
from app.services.rag.embeddings import generate_embeddings


def retrieve_relevant_chunks(
    query: str,
    top_k: int = 4,
    allowed_documents: list[str] | None = None
) -> tuple[list[str], list[dict]]:
    collection = get_or_create_collection()

    where_filter = None
    if allowed_documents:
        if len(allowed_documents) == 1:
            where_filter = {"source": allowed_documents[0]}
        else:
            where_filter = {"$or": [{"source": doc_name} for doc_name in allowed_documents]}

    query_embedding = generate_embeddings([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter
    )

    documents = results["documents"][0] if results.get("documents") else []
    metadatas = results["metadatas"][0] if results.get("metadatas") else []

    return documents, metadatas