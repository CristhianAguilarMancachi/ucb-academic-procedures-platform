from __future__ import annotations

import time

import requests

from app.core.config import (
    JINA_API_BASE_URL,
    JINA_API_KEY,
    JINA_EMBEDDING_DIMENSION,
    JINA_EMBEDDING_MODEL,
    JINA_MAX_RETRIES,
    JINA_TIMEOUT_SECONDS,
)


# ============================================================
# ERRORES DE EMBEDDINGS
# ============================================================

class JinaEmbeddingError(RuntimeError):
    """
    Error producido al generar embeddings mediante Jina AI.
    """


# ============================================================
# SESIÓN HTTP
# ============================================================

_session = requests.Session()

_session.headers.update(
    {
        "Authorization": f"Bearer {JINA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
)


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_embeddings(
    embeddings: list[list[float]],
    expected_count: int,
) -> None:
    """
    Verifica cantidad y dimensión de los embeddings recibidos.
    """

    if len(embeddings) != expected_count:
        raise JinaEmbeddingError(
            "Jina no devolvió la cantidad esperada "
            "de embeddings."
        )

    for embedding in embeddings:
        if (
            len(embedding)
            != JINA_EMBEDDING_DIMENSION
        ):
            raise JinaEmbeddingError(
                "Jina devolvió una dimensión distinta "
                "a la configurada."
            )


# ============================================================
# PETICIÓN A JINA
# ============================================================

def request_embeddings(
    texts: list[str],
    task: str,
) -> list[list[float]]:
    """
    Envía un lote de textos a Jina y devuelve sus embeddings
    respetando el orden original de entrada.
    """

    if not texts:
        return []

    payload = {
        "model": JINA_EMBEDDING_MODEL,
        "task": task,
        "dimensions": JINA_EMBEDDING_DIMENSION,
        "input": texts,
    }

    endpoint = (
        f"{JINA_API_BASE_URL}/embeddings"
    )

    last_error: Exception | None = None

    attempts = (
        JINA_MAX_RETRIES
        + 1
    )

    for attempt in range(
        attempts
    ):
        try:
            response = _session.post(
                endpoint,
                json=payload,
                timeout=JINA_TIMEOUT_SECONDS,
            )

            if response.status_code == 429:
                if attempt >= JINA_MAX_RETRIES:
                    raise JinaEmbeddingError(
                        "Jina alcanzó su límite temporal "
                        "de solicitudes."
                    )

                retry_after = response.headers.get(
                    "Retry-After"
                )

                try:
                    wait_seconds = float(
                        retry_after
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    wait_seconds = min(
                        2 ** attempt,
                        8,
                    )

                time.sleep(
                    max(
                        wait_seconds,
                        1.0,
                    )
                )

                continue

            if (
                500 <= response.status_code < 600
            ):
                if attempt >= JINA_MAX_RETRIES:
                    response.raise_for_status()

                time.sleep(
                    min(
                        2 ** attempt,
                        8,
                    )
                )

                continue

            response.raise_for_status()

            body = response.json()

            data = body.get(
                "data"
            )

            if not isinstance(
                data,
                list,
            ):
                raise JinaEmbeddingError(
                    "La respuesta de Jina no contiene "
                    "una lista válida de embeddings."
                )

            ordered_data = sorted(
                data,
                key=lambda item: item.get(
                    "index",
                    0,
                ),
            )

            embeddings = [
                item["embedding"]
                for item in ordered_data
            ]

            validate_embeddings(
                embeddings=embeddings,
                expected_count=len(texts),
            )

            return embeddings

        except JinaEmbeddingError:
            raise

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            last_error = exc

            if attempt >= JINA_MAX_RETRIES:
                break

            time.sleep(
                min(
                    2 ** attempt,
                    8,
                )
            )

    raise JinaEmbeddingError(
        "No fue posible generar embeddings "
        "mediante Jina AI."
    ) from last_error


# ============================================================
# EMBEDDINGS DE CONSULTAS
# ============================================================

def generate_query_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """
    Genera embeddings para una o varias consultas del usuario.

    Todas las consultas se envían juntas en una sola petición
    para conservar el batching utilizado por el retriever.
    """

    if not texts:
        return []

    cleaned_texts: list[str] = []

    for text in texts:
        cleaned_text = text.strip()

        if not cleaned_text:
            raise ValueError(
                "No se puede generar el embedding "
                "de una consulta vacía."
            )

        cleaned_texts.append(
            cleaned_text
        )

    return request_embeddings(
        texts=cleaned_texts,
        task="retrieval.query",
    )


def generate_embedding(
    text: str,
) -> list[float]:
    """
    Genera el embedding de una única consulta.
    """

    return generate_query_embeddings(
        [
            text,
        ]
    )[0]


# ============================================================
# EMBEDDINGS DE DOCUMENTOS
# ============================================================

def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    """
    Genera embeddings para chunks documentales.

    Se utiliza retrieval.passage porque estos vectores son los
    que posteriormente se almacenan en PostgreSQL + pgvector.
    """

    cleaned_texts = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]

    if not cleaned_texts:
        return []

    return request_embeddings(
        texts=cleaned_texts,
        task="retrieval.passage",
    )