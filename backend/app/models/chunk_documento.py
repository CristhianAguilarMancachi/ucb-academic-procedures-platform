from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class ChunkDocumento(Base):
    __tablename__ = "chunk_documento"

    # ========================================================
    # IDENTIFICACIÓN Y RELACIÓN DOCUMENTAL
    # ========================================================

    id_chunk_documento: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    id_version_documento: Mapped[int] = mapped_column(
        ForeignKey(
            "version_documento.id_version_documento"
        ),
        nullable=False,
    )

    # ========================================================
    # CONTENIDO Y METADATOS DEL CHUNK
    # ========================================================

    contenido: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    numero_chunk: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    pagina_inicio: Mapped[int | None] = mapped_column(
        Integer
    )

    pagina_fin: Mapped[int | None] = mapped_column(
        Integer
    )

    seccion: Mapped[str | None] = mapped_column(
        String(255)
    )

    subseccion: Mapped[str | None] = mapped_column(
        String(255)
    )

    articulo_numero: Mapped[str | None] = mapped_column(
        String(50)
    )

    estrategia_chunking: Mapped[str | None] = mapped_column(
        String(100)
    )

    tokens_aproximados: Mapped[int | None] = mapped_column(
        Integer
    )

    # ========================================================
    # VECTOR SEMÁNTICO
    # ========================================================
    #
    # Los embeddings son generados por Jina AI con una
    # dimensión fija de 512 valores.
    # ========================================================

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(512)
    )

    # ========================================================
    # CONTROL DEL REGISTRO
    # ========================================================

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    fecha_creacion: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    version_documento = relationship(
        "VersionDocumento",
        back_populates="chunks",
    )