from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.chunk_documento import ChunkDocumento
from app.models.version_documento import VersionDocumento
from app.models.documento_institucional import DocumentoInstitucional


def search_similar_chunks(
    db: Session,
    query_embedding: list[float],
    top_k: int = 4,
    allowed_documents: list[str] | None = None
) -> list[ChunkDocumento]:
    stmt = (
        select(ChunkDocumento)
        .join(VersionDocumento, ChunkDocumento.id_version_documento == VersionDocumento.id_version_documento)
        .join(
            DocumentoInstitucional,
            VersionDocumento.id_documento_institucional == DocumentoInstitucional.id_documento_institucional
        )
        .options(
            joinedload(ChunkDocumento.version_documento).joinedload(VersionDocumento.documento)
        )
        .where(ChunkDocumento.activo.is_(True))
        .where(ChunkDocumento.embedding.is_not(None))
    )

    if allowed_documents:
        stmt = stmt.where(DocumentoInstitucional.titulo.in_(allowed_documents))

    stmt = stmt.order_by(ChunkDocumento.embedding.cosine_distance(query_embedding)).limit(top_k)

    return list(db.scalars(stmt).all())