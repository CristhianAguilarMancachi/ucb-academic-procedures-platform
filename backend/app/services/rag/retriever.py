from app.core.config import TOP_K
from app.services.rag.embeddings import generate_embeddings
from app.services.rag.vector_store import get_or_create_collection


def retrieve_relevant_chunks(query: str, top_k: int = TOP_K) -> dict:
    collection = get_or_create_collection()
    query_embedding = generate_embeddings([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results