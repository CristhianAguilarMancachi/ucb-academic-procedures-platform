from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.tramite_campo import TramiteCampo
    from app.models.gestion_seguimiento.tramite_etapa import TramiteEtapa
    from app.models.gestion_seguimiento.tramite_requisito import (
        TramiteRequisito,
    )


class Tramite(Base):
    """
    Representa un trámite académico disponible en el catálogo.

    El catálogo describe qué trámite existe y su información
    configurable, pero no presupone ni codifica el proceso
    administrativo interno que seguirá posteriormente.
    """

    __tablename__ = "tramite"

    tiempo_estimado: Mapped[str | None] = mapped_column(Text)
    canales_atencion: Mapped[str | None] = mapped_column(Text)
    instrucciones: Mapped[str | None] = mapped_column(Text)
    condiciones: Mapped[str | None] = mapped_column(Text)
    tipo_finalizacion: Mapped[str | None] = mapped_column(String(30))


    id_tramite: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    publicado: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    permite_solicitudes: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    requisitos: Mapped[list[TramiteRequisito]] = relationship(
        "TramiteRequisito",
        back_populates="tramite",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    campos: Mapped[list[TramiteCampo]] = relationship(
        "TramiteCampo",
        back_populates="tramite",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    etapas: Mapped[list[TramiteEtapa]] = relationship(
        "TramiteEtapa",
        back_populates="tramite",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        CheckConstraint("tipo_finalizacion IN ('entrega', 'resultado_registrado', 'externo')", name="ck_tramite_tipo_finalizacion"),

        CheckConstraint(
            "LENGTH(TRIM(nombre)) >= 3",
            name="ck_tramite_nombre_no_vacio",
        ),
        CheckConstraint(
            """
            publicado = FALSE
            OR activo = TRUE
            """,
            name="ck_tramite_publicacion",
        ),
        CheckConstraint(
            """
            permite_solicitudes = FALSE
            OR
            (
                activo = TRUE
                AND publicado = TRUE
            )
            """,
            name="ck_tramite_permite_solicitudes",
        ),
        Index(
            "idx_tramite_activo",
            "activo",
        ),
        Index(
            "idx_tramite_publicado",
            "publicado",
        ),
        Index(
            "idx_tramite_catalogo",
            "activo",
            "publicado",
        ),
    )

    @property
    def visible_en_catalogo(self) -> bool:
        """Indica si el trámite puede mostrarse en el catálogo."""
        return self.activo and self.publicado

    @property
    def disponible_para_solicitud(self) -> bool:
        """Indica si actualmente admite nuevas solicitudes."""
        return (
            self.activo
            and self.publicado
            and self.permite_solicitudes
        )

    def __repr__(self) -> str:
        return (
            "Tramite("
            f"id_tramite={self.id_tramite!r}, "
            f"nombre={self.nombre!r}, "
            f"activo={self.activo!r}, "
            f"publicado={self.publicado!r}, "
            f"permite_solicitudes={self.permite_solicitudes!r}"
            ")"
        )