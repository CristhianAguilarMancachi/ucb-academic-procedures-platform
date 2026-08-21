from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class PerfilAcademico(Base):
    __tablename__ = "perfil_academico"

    id_perfil: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_usuario: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "usuario.id_usuario",
            name="fk_perfil_academico_usuario",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    codigo_estudiante: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    sede: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    carrera_programa: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    nivel_academico: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    documento_identidad: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        foreign_keys=[id_usuario],
    )

    __table_args__ = (
        UniqueConstraint(
            "id_usuario",
            name="uq_perfil_academico_usuario",
        ),
        CheckConstraint(
            """
            codigo_estudiante IS NULL
            OR LENGTH(TRIM(codigo_estudiante)) >= 1
            """,
            name="ck_perfil_academico_codigo_estudiante",
        ),
        CheckConstraint(
            """
            sede IS NULL
            OR LENGTH(TRIM(sede)) >= 2
            """,
            name="ck_perfil_academico_sede",
        ),
        CheckConstraint(
            """
            carrera_programa IS NULL
            OR LENGTH(TRIM(carrera_programa)) >= 2
            """,
            name="ck_perfil_academico_carrera_programa",
        ),
        CheckConstraint(
            """
            nivel_academico IS NULL
            OR LENGTH(TRIM(nivel_academico)) >= 2
            """,
            name="ck_perfil_academico_nivel_academico",
        ),
        CheckConstraint(
            """
            documento_identidad IS NULL
            OR LENGTH(TRIM(documento_identidad)) >= 3
            """,
            name="ck_perfil_academico_documento_identidad",
        ),
        Index(
            "idx_perfil_academico_codigo_estudiante",
            "codigo_estudiante",
            postgresql_where=text(
                "codigo_estudiante IS NOT NULL"
            ),
        ),
        Index(
            "idx_perfil_academico_documento_identidad",
            "documento_identidad",
            postgresql_where=text(
                "documento_identidad IS NOT NULL"
            ),
        ),
    )