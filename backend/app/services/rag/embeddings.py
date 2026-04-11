from sentence_transformers import SentenceTransformer
from app.core.config import EMBEDDING_MODEL


_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model

    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    return _embedding_model


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()