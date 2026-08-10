from threading import Lock

from sentence_transformers import SentenceTransformer

from app.core.config import EMBEDDING_MODEL


_embedding_model: SentenceTransformer | None = None
_embedding_model_lock = Lock()


def get_embedding_model() -> SentenceTransformer:
    """
    Devuelve una única instancia compartida del modelo de embeddings.

    El modelo se carga solamente la primera vez que se necesita.
    Las siguientes llamadas reutilizan la misma instancia.
    """
    global _embedding_model

    if _embedding_model is None:
        with _embedding_model_lock:
            if _embedding_model is None:
                print(
                    f"[INFO] Cargando modelo de embeddings: "
                    f"{EMBEDDING_MODEL}"
                )

                _embedding_model = SentenceTransformer(
                    EMBEDDING_MODEL
                )

                print(
                    "[INFO] Modelo de embeddings cargado correctamente."
                )

    return _embedding_model


def generate_embedding(text: str) -> list[float]:
    """
    Genera el embedding de un único texto.
    """
    if not text or not text.strip():
        raise ValueError(
            "No se puede generar el embedding de un texto vacío."
        )

    model = get_embedding_model()

    embedding = model.encode(
        text,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embedding.tolist()


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """
    Genera embeddings para una lista de textos.
    """
    cleaned_texts = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]

    if not cleaned_texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        cleaned_texts,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()