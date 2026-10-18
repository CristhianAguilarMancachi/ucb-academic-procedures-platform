from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.tramite import Tramite
    from app.models.gestion_seguimiento.unidad_administrativa import (
        UnidadAdministrativa,
    )


class TramiteEtapa(Base):
    """
    Representa una etapa configurable perteneciente a un trámite.

    Esta entidad deja preparada la infraestructura necesaria para
    definir posteriormente los procesos internos institucionales.

    La existencia de este modelo NO implica que actualmente conozcamos
    las etapas reales de los trámites. No deben cargarse etapas,
    unidades ni secuencias mientras esa información no haya sido
    confirmada institucionalmente.
    """

    __tablename__ = "tramite_etapa"

    visible_solicitante: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


    id_etapa: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_tramite: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite.id_tramite",
            ondelete="CASCADE",
            name="fk_tramite_etapa_tramite",
        ),
        nullable=False,
    )

    id_unidad: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "unidad_administrativa.id_unidad",
            ondelete="RESTRICT",
            name="fk_tramite_etapa_unidad",
        ),
        nullable=True,
    )

    nombre: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    es_inicial: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    es_final: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    tramite: Mapped[Tramite] = relationship(
        "Tramite",
    )

    unidad: Mapped[UnidadAdministrativa | None] = relationship(
        "UnidadAdministrativa",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint("id_tramite", "id_etapa", name="uq_tramite_etapa_pertenencia"),
        UniqueConstraint(
            "id_tramite",
            "orden",
            name="uq_tramite_etapa_orden",
        ),
        CheckConstraint(
            "LENGTH(TRIM(nombre)) >= 2",
            name="ck_tramite_etapa_nombre_no_vacio",
        ),
        CheckConstraint(
            "orden > 0",
            name="ck_tramite_etapa_orden",
        ),
        Index(
            "idx_tramite_etapa_tramite",
            "id_tramite",
        ),
        Index(
            "idx_tramite_etapa_unidad",
            "id_unidad",
        ),
        Index(
            "idx_tramite_etapa_tramite_activo",
            "id_tramite",
            "activo",
        ),
        Index(
            "uq_tramite_etapa_inicial_activa",
            "id_tramite",
            unique=True,
            postgresql_where=text(
                "es_inicial = TRUE AND activo = TRUE"
            ),
        ),
        Index(
            "uq_tramite_etapa_final_activa",
            "id_tramite",
            unique=True,
            postgresql_where=text(
                "es_final = TRUE AND activo = TRUE"
            ),
        ),
    )

    @property
    def esta_activa(self) -> bool:
        """Indica si la etapa se encuentra habilitada."""
        return self.activo

    def __repr__(self) -> str:
        return (
            "TramiteEtapa("
            f"id_etapa={self.id_etapa!r}, "
            f"id_tramite={self.id_tramite!r}, "
            f"id_unidad={self.id_unidad!r}, "
            f"nombre={self.nombre!r}, "
            f"orden={self.orden!r}, "
            f"es_inicial={self.es_inicial!r}, "
            f"es_final={self.es_final!r}, "
            f"activo={self.activo!r}"
            ")"
        )