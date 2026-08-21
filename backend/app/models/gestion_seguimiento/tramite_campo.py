from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.gestion_seguimiento.tramite import Tramite


class TramiteCampo(Base):
    """
    Define un dato configurable que puede ser solicitado para
    un trámite concreto.

    Permite que diferentes trámites soliciten información distinta
    sin agregar columnas específicas a la tabla de solicitudes.

    La configuración adicional se almacena en JSONB únicamente
    para reglas particulares del campo, como opciones disponibles
    en un campo de selección.
    """

    __tablename__ = "tramite_campo"

    id_campo: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    id_tramite: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "tramite.id_tramite",
            ondelete="CASCADE",
            name="fk_tramite_campo_tramite",
        ),
        nullable=False,
    )

    clave: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    etiqueta: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    descripcion: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    tipo_dato: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    obligatorio: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    orden: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    configuracion: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
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
        back_populates="campos",
    )

    # =====================================================
    # RESTRICCIONES E ÍNDICES
    # =====================================================

    __table_args__ = (
        UniqueConstraint(
            "id_tramite",
            "clave",
            name="uq_tramite_campo_clave",
        ),
        CheckConstraint(
            "LENGTH(TRIM(clave)) >= 2",
            name="ck_tramite_campo_clave_no_vacia",
        ),
        CheckConstraint(
            "LENGTH(TRIM(etiqueta)) >= 2",
            name="ck_tramite_campo_etiqueta_no_vacia",
        ),
        CheckConstraint(
            """
            tipo_dato IN (
                'texto',
                'texto_largo',
                'entero',
                'decimal',
                'fecha',
                'booleano',
                'seleccion'
            )
            """,
            name="ck_tramite_campo_tipo_dato",
        ),
        CheckConstraint(
            "orden > 0",
            name="ck_tramite_campo_orden",
        ),
        Index(
            "idx_tramite_campo_tramite",
            "id_tramite",
        ),
        Index(
            "idx_tramite_campo_tramite_activo",
            "id_tramite",
            "activo",
        ),
        Index(
            "idx_tramite_campo_orden",
            "id_tramite",
            "orden",
        ),
    )

    @property
    def esta_activo(self) -> bool:
        """Indica si el campo continúa habilitado para el trámite."""
        return self.activo

    @property
    def requiere_opciones(self) -> bool:
        """
        Indica si el tipo de campo necesita una lista de opciones
        configuradas.
        """
        return self.tipo_dato == "seleccion"

    def __repr__(self) -> str:
        return (
            "TramiteCampo("
            f"id_campo={self.id_campo!r}, "
            f"id_tramite={self.id_tramite!r}, "
            f"clave={self.clave!r}, "
            f"tipo_dato={self.tipo_dato!r}, "
            f"obligatorio={self.obligatorio!r}, "
            f"activo={self.activo!r}"
            ")"
        )