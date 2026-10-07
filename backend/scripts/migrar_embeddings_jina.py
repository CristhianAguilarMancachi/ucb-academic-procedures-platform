from __future__ import annotations

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.rag.embeddings import (
    generate_embeddings,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

BATCH_SIZE = 16


# ============================================================
# UTILIDADES
# ============================================================

def vector_to_postgres(
    embedding: list[float],
) -> str:
    """
    Convierte una lista de floats al formato textual esperado
    por pgvector.
    """

    return (
        "["
        + ",".join(
            str(value)
            for value in embedding
        )
        + "]"
    )


# ============================================================
# MIGRACIÓN
# ============================================================

def migrar_embeddings() -> None:
    """
    Regenera con Jina AI los embeddings de los chunks activos.

    Solo procesa chunks cuyo embedding sea NULL, por lo que el
    proceso puede reanudarse de forma segura si se interrumpe.
    """

    db = SessionLocal()

    try:
        total_activos = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM chunk_documento
                WHERE activo = TRUE
                """
            )
        ).scalar_one()

        total_con_embedding = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM chunk_documento
                WHERE activo = TRUE
                  AND embedding IS NOT NULL
                """
            )
        ).scalar_one()

        total_pendientes = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM chunk_documento
                WHERE activo = TRUE
                  AND embedding IS NULL
                """
            )
        ).scalar_one()

        print(
            f"[JINA] Chunks activos: {total_activos}"
        )
        print(
            f"[JINA] Chunks con embedding: "
            f"{total_con_embedding}"
        )
        print(
            f"[JINA] Chunks pendientes: "
            f"{total_pendientes}"
        )

        if total_pendientes == 0:
            print(
                "[JINA] No existen chunks pendientes."
            )
            return

        procesados = 0

        while True:
            rows = db.execute(
                text(
                    """
                    SELECT
                        id_chunk_documento,
                        contenido
                    FROM chunk_documento
                    WHERE activo = TRUE
                      AND embedding IS NULL
                    ORDER BY id_chunk_documento
                    LIMIT :batch_size
                    """
                ),
                {
                    "batch_size": BATCH_SIZE,
                },
            ).mappings().all()

            if not rows:
                break

            textos = [
                row["contenido"]
                for row in rows
            ]

            ids = [
                row["id_chunk_documento"]
                for row in rows
            ]

            inicio = (
                procesados
                + 1
            )

            fin = (
                procesados
                + len(rows)
            )

            print(
                f"[JINA] Generando embeddings "
                f"{inicio}-{fin} "
                f"de {total_pendientes}..."
            )

            embeddings = generate_embeddings(
                textos
            )

            if (
                len(embeddings)
                != len(rows)
            ):
                raise RuntimeError(
                    "La cantidad de embeddings generados "
                    "no coincide con la cantidad de chunks."
                )

            for (
                chunk_id,
                embedding,
            ) in zip(
                ids,
                embeddings,
            ):
                db.execute(
                    text(
                        """
                        UPDATE chunk_documento
                        SET embedding = CAST(
                            :embedding AS vector
                        )
                        WHERE id_chunk_documento = :chunk_id
                        """
                    ),
                    {
                        "chunk_id": chunk_id,
                        "embedding": vector_to_postgres(
                            embedding
                        ),
                    },
                )

            db.commit()

            procesados += len(rows)

            print(
                f"[JINA] Lote guardado. "
                f"Procesados: {procesados}/"
                f"{total_pendientes}"
            )

        restantes = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM chunk_documento
                WHERE activo = TRUE
                  AND embedding IS NULL
                """
            )
        ).scalar_one()

        total_final = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM chunk_documento
                WHERE activo = TRUE
                  AND embedding IS NOT NULL
                """
            )
        ).scalar_one()

        print()
        print(
            "[JINA] Migración finalizada."
        )
        print(
            f"[JINA] Chunks con embedding: "
            f"{total_final}"
        )
        print(
            f"[JINA] Chunks pendientes: "
            f"{restantes}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    migrar_embeddings()