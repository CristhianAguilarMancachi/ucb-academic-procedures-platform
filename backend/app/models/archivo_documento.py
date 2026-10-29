
from datetime import datetime

from sqlalchemy import (
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ArchivoDocumento(Base):
    __tablename__ = "archivo_documento"

    id_version_documento: Mapped[int] = mapped_column(
        ForeignKey(
            "version_documento.id_version_documento",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    nombre_archivo_original: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    contenido_pdf: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    tamano_bytes: Mapped[int] = mapped_column(
        Integer,
        Computed(
            "octet_length(contenido_pdf)",
            persisted=True,
        ),
        nullable=False,
    )

    fecha_almacenamiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
