
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento.tramite import Tramite
from app.models.gestion_seguimiento.tramite_campo import TramiteCampo
from app.models.gestion_seguimiento.tramite_requisito import (
    TramiteRequisito,
)
from app.models.gestion_seguimiento.tramite_requisito_economico import (
    TramiteRequisitoEconomico,
)


# ============================================================
# TRÁMITES
# ============================================================

def crear_tramite(
    db: Session,
    *,
    nombre: str,
    descripcion: str | None = None,
    activo: bool = True,
    publicado: bool = False,
    permite_solicitudes: bool = False,
) -> Tramite:
    tramite = Tramite(
        nombre=nombre,
        descripcion=descripcion,
        activo=activo,
        publicado=publicado,
        permite_solicitudes=permite_solicitudes,
    )

    db.add(tramite)
    db.flush()
    db.refresh(tramite)
    return tramite


def obtener_tramite_por_id(
    db: Session,
    id_tramite: int,
) -> Tramite | None:
    return db.get(Tramite, id_tramite)


def obtener_tramite_por_id_completo(
    db: Session,
    id_tramite: int,
) -> Tramite | None:
    consulta = (
        select(Tramite)
        .where(Tramite.id_tramite == id_tramite)
        .options(
            selectinload(
                Tramite.requisitos
            ).selectinload(
                TramiteRequisito.configuraciones_economicas
            ),
            selectinload(Tramite.campos),
        )
    )

    return db.scalars(consulta).unique().one_or_none()


def obtener_tramite_por_nombre(
    db: Session,
    nombre: str,
) -> Tramite | None:
    nombre_normalizado = nombre.strip().lower()

    consulta = select(Tramite).where(
        func.lower(Tramite.nombre) == nombre_normalizado
    )

    return db.scalars(consulta).one_or_none()


def existe_tramite(
    db: Session,
    id_tramite: int,
) -> bool:
    consulta = select(
        select(Tramite.id_tramite)
        .where(Tramite.id_tramite == id_tramite)
        .exists()
    )
    return bool(db.scalar(consulta))


def listar_tramites(
    db: Session,
    *,
    pagina: int = 1,
    por_pagina: int = 20,
    activo: bool | None = None,
    publicado: bool | None = None,
    permite_solicitudes: bool | None = None,
    texto_busqueda: str | None = None,
) -> tuple[Sequence[Tramite], int]:
    pagina = max(pagina, 1)
    por_pagina = min(max(por_pagina, 1), 100)

    filtros = []

    if activo is not None:
        filtros.append(Tramite.activo.is_(activo))

    if publicado is not None:
        filtros.append(Tramite.publicado.is_(publicado))

    if permite_solicitudes is not None:
        filtros.append(
            Tramite.permite_solicitudes.is_(permite_solicitudes)
        )

    if texto_busqueda:
        patron = f"%{texto_busqueda.strip()}%"
        filtros.append(
            Tramite.nombre.ilike(patron)
            | Tramite.descripcion.ilike(patron)
        )

    consulta_base = select(Tramite)

    if filtros:
        consulta_base = consulta_base.where(*filtros)

    subconsulta = consulta_base.with_only_columns(
        Tramite.id_tramite
    ).subquery()

    total = db.scalar(
        select(func.count()).select_from(subconsulta)
    ) or 0

    consulta = (
        consulta_base
        .options(selectinload(Tramite.requisitos))
        .order_by(Tramite.nombre.asc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
    )

    return db.scalars(consulta).all(), int(total)


def listar_catalogo_publicado(
    db: Session,
) -> Sequence[Tramite]:
    consulta = (
        select(Tramite)
        .where(
            Tramite.activo.is_(True),
            Tramite.publicado.is_(True),
        )
        .order_by(Tramite.nombre.asc())
    )

    return db.scalars(consulta).all()


def actualizar_tramite(
    db: Session,
    tramite: Tramite,
    *,
    nombre: str | None = None,
    descripcion: str | None = None,
    activo: bool | None = None,
    publicado: bool | None = None,
    permite_solicitudes: bool | None = None,
    actualizar_descripcion: bool = False,
) -> Tramite:
    if nombre is not None:
        tramite.nombre = nombre

    if actualizar_descripcion:
        tramite.descripcion = descripcion

    if activo is not None:
        tramite.activo = activo

    if publicado is not None:
        tramite.publicado = publicado

    if permite_solicitudes is not None:
        tramite.permite_solicitudes = permite_solicitudes

    db.flush()
    db.refresh(tramite)
    return tramite


# ============================================================
# REQUISITOS
# ============================================================

def crear_requisito(
    db: Session,
    *,
    id_tramite: int,
    nombre: str,
    descripcion: str | None,
    obligatorio: bool,
    orden: int,
    activo: bool,
) -> TramiteRequisito:
    requisito = TramiteRequisito(
        id_tramite=id_tramite,
        nombre=nombre,
        descripcion=descripcion,
        obligatorio=obligatorio,
        orden=orden,
        activo=activo,
    )

    db.add(requisito)
    db.flush()
    db.refresh(requisito)
    return requisito


def obtener_requisito_por_id(
    db: Session,
    id_requisito: int,
) -> TramiteRequisito | None:
    consulta = (
        select(TramiteRequisito)
        .where(TramiteRequisito.id_requisito == id_requisito)
        .options(
            selectinload(
                TramiteRequisito.configuraciones_economicas
            )
        )
    )

    return db.scalars(consulta).one_or_none()


def obtener_requisito_por_nombre(
    db: Session,
    *,
    id_tramite: int,
    nombre: str,
) -> TramiteRequisito | None:
    consulta = select(TramiteRequisito).where(
        TramiteRequisito.id_tramite == id_tramite,
        func.lower(TramiteRequisito.nombre)
        == nombre.strip().lower(),
    )

    return db.scalars(consulta).one_or_none()


def listar_requisitos_tramite(
    db: Session,
    id_tramite: int,
    *,
    solo_activos: bool = False,
) -> Sequence[TramiteRequisito]:
    consulta = (
        select(TramiteRequisito)
        .where(TramiteRequisito.id_tramite == id_tramite)
        .options(
            selectinload(
                TramiteRequisito.configuraciones_economicas
            )
        )
        .order_by(
            TramiteRequisito.orden.asc(),
            TramiteRequisito.id_requisito.asc(),
        )
    )

    if solo_activos:
        consulta = consulta.where(
            TramiteRequisito.activo.is_(True)
        )

    return db.scalars(consulta).all()


def actualizar_requisito(
    db: Session,
    requisito: TramiteRequisito,
    *,
    nombre: str | None = None,
    descripcion: str | None = None,
    obligatorio: bool | None = None,
    orden: int | None = None,
    activo: bool | None = None,
    actualizar_descripcion: bool = False,
) -> TramiteRequisito:
    if nombre is not None:
        requisito.nombre = nombre

    if actualizar_descripcion:
        requisito.descripcion = descripcion

    if obligatorio is not None:
        requisito.obligatorio = obligatorio

    if orden is not None:
        requisito.orden = orden

    if activo is not None:
        requisito.activo = activo

    db.flush()
    db.refresh(requisito)
    return requisito


# ============================================================
# CONFIGURACIÓN ECONÓMICA
# ============================================================

def crear_configuracion_economica(
    db: Session,
    *,
    id_requisito: int,
    concepto: str,
    monto: Decimal,
    moneda: str,
    gestion: int,
    codigo_concepto_externo: str | None,
    activo: bool,
) -> TramiteRequisitoEconomico:
    configuracion = TramiteRequisitoEconomico(
        id_requisito=id_requisito,
        concepto=concepto,
        monto=monto,
        moneda=moneda,
        gestion=gestion,
        codigo_concepto_externo=codigo_concepto_externo,
        activo=activo,
    )

    db.add(configuracion)
    db.flush()
    db.refresh(configuracion)
    return configuracion


def obtener_configuracion_economica_por_id(
    db: Session,
    id_requisito_economico: int,
) -> TramiteRequisitoEconomico | None:
    return db.get(
        TramiteRequisitoEconomico,
        id_requisito_economico,
    )


def obtener_configuracion_economica_por_gestion(
    db: Session,
    *,
    id_requisito: int,
    gestion: int,
) -> TramiteRequisitoEconomico | None:
    consulta = select(TramiteRequisitoEconomico).where(
        TramiteRequisitoEconomico.id_requisito == id_requisito,
        TramiteRequisitoEconomico.gestion == gestion,
    )

    return db.scalars(consulta).one_or_none()


def listar_configuraciones_economicas(
    db: Session,
    id_requisito: int,
    *,
    solo_activas: bool = False,
) -> Sequence[TramiteRequisitoEconomico]:
    consulta = (
        select(TramiteRequisitoEconomico)
        .where(
            TramiteRequisitoEconomico.id_requisito
            == id_requisito
        )
        .order_by(
            TramiteRequisitoEconomico.gestion.desc()
        )
    )

    if solo_activas:
        consulta = consulta.where(
            TramiteRequisitoEconomico.activo.is_(True)
        )

    return db.scalars(consulta).all()


def actualizar_configuracion_economica(
    db: Session,
    configuracion: TramiteRequisitoEconomico,
    *,
    concepto: str | None = None,
    monto: Decimal | None = None,
    moneda: str | None = None,
    gestion: int | None = None,
    codigo_concepto_externo: str | None = None,
    activo: bool | None = None,
    actualizar_codigo_externo: bool = False,
) -> TramiteRequisitoEconomico:
    if concepto is not None:
        configuracion.concepto = concepto

    if monto is not None:
        configuracion.monto = monto

    if moneda is not None:
        configuracion.moneda = moneda

    if gestion is not None:
        configuracion.gestion = gestion

    if actualizar_codigo_externo:
        configuracion.codigo_concepto_externo = (
            codigo_concepto_externo
        )

    if activo is not None:
        configuracion.activo = activo

    db.flush()
    db.refresh(configuracion)
    return configuracion


# ============================================================
# CAMPOS CONFIGURABLES
# ============================================================

def crear_campo(
    db: Session,
    *,
    id_tramite: int,
    clave: str,
    etiqueta: str,
    descripcion: str | None,
    tipo_dato: str,
    obligatorio: bool,
    orden: int,
    configuracion: dict | None,
    activo: bool,
) -> TramiteCampo:
    campo = TramiteCampo(
        id_tramite=id_tramite,
        clave=clave,
        etiqueta=etiqueta,
        descripcion=descripcion,
        tipo_dato=tipo_dato,
        obligatorio=obligatorio,
        orden=orden,
        configuracion=configuracion,
        activo=activo,
    )

    db.add(campo)
    db.flush()
    db.refresh(campo)
    return campo


def obtener_campo_por_id(
    db: Session,
    id_campo: int,
) -> TramiteCampo | None:
    return db.get(TramiteCampo, id_campo)


def obtener_campo_por_clave(
    db: Session,
    *,
    id_tramite: int,
    clave: str,
) -> TramiteCampo | None:
    consulta = select(TramiteCampo).where(
        TramiteCampo.id_tramite == id_tramite,
        TramiteCampo.clave == clave.strip().lower(),
    )

    return db.scalars(consulta).one_or_none()


def listar_campos_tramite(
    db: Session,
    id_tramite: int,
    *,
    solo_activos: bool = False,
) -> Sequence[TramiteCampo]:
    consulta = (
        select(TramiteCampo)
        .where(TramiteCampo.id_tramite == id_tramite)
        .order_by(
            TramiteCampo.orden.asc(),
            TramiteCampo.id_campo.asc(),
        )
    )

    if solo_activos:
        consulta = consulta.where(
            TramiteCampo.activo.is_(True)
        )

    return db.scalars(consulta).all()


def actualizar_campo(
    db: Session,
    campo: TramiteCampo,
    *,
    clave: str | None = None,
    etiqueta: str | None = None,
    descripcion: str | None = None,
    tipo_dato: str | None = None,
    obligatorio: bool | None = None,
    orden: int | None = None,
    configuracion: dict | None = None,
    activo: bool | None = None,
    actualizar_descripcion: bool = False,
    actualizar_configuracion: bool = False,
) -> TramiteCampo:
    if clave is not None:
        campo.clave = clave

    if etiqueta is not None:
        campo.etiqueta = etiqueta

    if actualizar_descripcion:
        campo.descripcion = descripcion

    if tipo_dato is not None:
        campo.tipo_dato = tipo_dato

    if obligatorio is not None:
        campo.obligatorio = obligatorio

    if orden is not None:
        campo.orden = orden

    if actualizar_configuracion:
        campo.configuracion = configuracion

    if activo is not None:
        campo.activo = activo

    db.flush()
    db.refresh(campo)
    return campo


# ============================================================
# BLOQUEO DE CONFIGURACIÓN
# ============================================================

def bloquear_configuracion(
    db: Session,
    id_tramite: int,
) -> Tramite | None:
    """
    Bloquea un trámite para operaciones administrativas
    que requieran acceso exclusivo a su configuración.
    """
    return db.scalar(
        select(Tramite)
        .where(Tramite.id_tramite == id_tramite)
        .with_for_update()
    )
