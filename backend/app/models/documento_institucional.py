
from sqlalchemy import String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DocumentoInstitucional(Base):
    __tablename__ = "documento_institucional"

    id_documento_institucional: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    titulo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    tipo_documento: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(Text)

    unidad_origen: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="activo",
    )

    fecha_publicacion: Mapped[Date | None] = mapped_column(Date)

    fecha_carga: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    hash_archivo: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    id_version_actual: Mapped[int | None] = mapped_column(
        ForeignKey("version_documento.id_version_documento")
    )

    fecha_creacion: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    fecha_actualizacion: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    versiones = relationship(
        "VersionDocumento",
        back_populates="documento",
        foreign_keys="VersionDocumento.id_documento_institucional",
    )

    version_actual = relationship(
        "VersionDocumento",
        foreign_keys=[id_version_actual],
        post_update=True,
    )
