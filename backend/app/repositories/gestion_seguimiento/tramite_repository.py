from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.gestion_seguimiento.tramite import (
    Tramite,
)
from app.models.gestion_seguimiento.tramite_campo import (
    TramiteCampo,
)
from app.models.gestion_seguimiento.tramite_etapa import (
    TramiteEtapa,
)
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
    """
    Crea un trámite en el catálogo.

    La transacción queda pendiente de confirmación
    por parte del service.
    """
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
    """
    Obtiene un trámite sin cargar relaciones adicionales.
    """
    return db.get(
        Tramite,
        id_tramite,
    )


def obtener_tramite_por_id_completo(
    db: Session,
    id_tramite: int,
) -> Tramite | None:
    """
    Obtiene un trámite con su configuración completa.
    """
    consulta = (
        select(Tramite)
        .where(
            Tramite.id_tramite == id_tramite,
        )
        .options(
            selectinload(
                Tramite.requisitos,
            ).selectinload(
                TramiteRequisito.configuraciones_economicas,
            ),
            selectinload(
                Tramite.campos,
            ),
            selectinload(
                Tramite.etapas,
            ).selectinload(
                TramiteEtapa.unidad,
            ),
        )
    )

    return db.scalars(
        consulta
    ).unique().one_or_none()


def obtener_tramite_por_nombre(
    db: Session,
    nombre: str,
) -> Tramite | None:
    """
    Busca un trámite por nombre ignorando diferencias
    de mayúsculas y minúsculas.
    """
    nombre_normalizado = nombre.strip().lower()

    consulta = select(
        Tramite
    ).where(
        func.lower(
            Tramite.nombre
        ) == nombre_normalizado
    )

    return db.scalars(
        consulta
    ).one_or_none()


def existe_tramite(
    db: Session,
    id_tramite: int,
) -> bool:
    """
    Indica si existe un trámite con el identificador recibido.
    """
    consulta = select(
        select(
            Tramite.id_tramite
        )
        .where(
            Tramite.id_tramite == id_tramite,
        )
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
    """
    Lista trámites con filtros administrativos y paginación.
    """
    pagina = max(pagina, 1)
    por_pagina = min(
        max(por_pagina, 1),
        100,
    )

    filtros = []

    if activo is not None:
        filtros.append(
            Tramite.activo.is_(activo)
        )

    if publicado is not None:
        filtros.append(
            Tramite.publicado.is_(publicado)
        )

    if permite_solicitudes is not None:
        filtros.append(
            Tramite.permite_solicitudes.is_(
                permite_solicitudes
            )
        )

    if texto_busqueda:
        patron = f"%{texto_busqueda.strip()}%"

        filtros.append(
            Tramite.nombre.ilike(patron)
            | Tramite.descripcion.ilike(patron)
        )

    consulta_base = select(Tramite)

    if filtros:
        consulta_base = consulta_base.where(
            *filtros
        )

    subconsulta = consulta_base.with_only_columns(
        Tramite.id_tramite
    ).subquery()

    total = db.scalar(
        select(func.count())
        .select_from(subconsulta)
    ) or 0

    consulta = (
        consulta_base
        .options(selectinload(Tramite.requisitos), selectinload(Tramite.etapas))
        .order_by(
            Tramite.nombre.asc(),
        )
        .offset(
            (pagina - 1) * por_pagina,
        )
        .limit(
            por_pagina,
        )
    )

    tramites = db.scalars(
        consulta
    ).all()

    return tramites, int(total)


def listar_catalogo_publicado(
    db: Session,
) -> Sequence[Tramite]:
    """
    Devuelve únicamente los trámites activos y publicados.
    """
    consulta = (
        select(Tramite)
        .where(
            Tramite.activo.is_(True),
            Tramite.publicado.is_(True),
        )
        .order_by(
            Tramite.nombre.asc(),
        )
    )

    return db.scalars(
        consulta
    ).all()


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
    """
    Actualiza la configuración general de un trámite.
    """
    if nombre is not None:
        tramite.nombre = nombre

    if actualizar_descripcion:
        tramite.descripcion = descripcion

    if activo is not None:
        tramite.activo = activo

    if publicado is not None:
        tramite.publicado = publicado

    if permite_solicitudes is not None:
        tramite.permite_solicitudes = (
            permite_solicitudes
        )

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
    """
    Crea un requisito asociado a un trámite.
    """
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
    """
    Obtiene un requisito con sus configuraciones económicas.
    """
    consulta = (
        select(TramiteRequisito)
        .where(
            TramiteRequisito.id_requisito
            == id_requisito,
        )
        .options(
            selectinload(
                TramiteRequisito.configuraciones_economicas,
            ),
        )
    )

    return db.scalars(
        consulta
    ).one_or_none()


def obtener_requisito_por_nombre(
    db: Session,
    *,
    id_tramite: int,
    nombre: str,
) -> TramiteRequisito | None:
    """
    Busca un requisito por nombre dentro de un trámite.
    """
    nombre_normalizado = nombre.strip().lower()

    consulta = select(
        TramiteRequisito
    ).where(
        TramiteRequisito.id_tramite
        == id_tramite,
        func.lower(
            TramiteRequisito.nombre
        ) == nombre_normalizado,
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_requisitos_tramite(
    db: Session,
    id_tramite: int,
    *,
    solo_activos: bool = False,
) -> Sequence[TramiteRequisito]:
    """
    Lista los requisitos configurados para un trámite.
    """
    consulta = (
        select(TramiteRequisito)
        .where(
            TramiteRequisito.id_tramite
            == id_tramite,
        )
        .options(
            selectinload(
                TramiteRequisito.configuraciones_economicas,
            ),
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

    return db.scalars(
        consulta
    ).all()


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
    """
    Modifica un requisito existente.
    """
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
    """
    Registra una configuración económica para un requisito.
    """
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
    """
    Obtiene una configuración económica por identificador.
    """
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
    """
    Obtiene la configuración económica de un requisito
    para una gestión determinada.
    """
    consulta = select(
        TramiteRequisitoEconomico
    ).where(
        TramiteRequisitoEconomico.id_requisito
        == id_requisito,
        TramiteRequisitoEconomico.gestion
        == gestion,
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_configuraciones_economicas(
    db: Session,
    id_requisito: int,
    *,
    solo_activas: bool = False,
) -> Sequence[TramiteRequisitoEconomico]:
    """
    Lista el histórico/configuración económica de un requisito.
    """
    consulta = (
        select(TramiteRequisitoEconomico)
        .where(
            TramiteRequisitoEconomico.id_requisito
            == id_requisito,
        )
        .order_by(
            TramiteRequisitoEconomico.gestion.desc(),
        )
    )

    if solo_activas:
        consulta = consulta.where(
            TramiteRequisitoEconomico.activo.is_(True)
        )

    return db.scalars(
        consulta
    ).all()


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
    """
    Modifica una configuración económica existente.
    """
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
    """
    Agrega un campo configurable a un trámite.
    """
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
    """
    Obtiene un campo configurable por identificador.
    """
    return db.get(
        TramiteCampo,
        id_campo,
    )


def obtener_campo_por_clave(
    db: Session,
    *,
    id_tramite: int,
    clave: str,
) -> TramiteCampo | None:
    """
    Busca una clave dentro de un trámite.
    """
    consulta = select(
        TramiteCampo
    ).where(
        TramiteCampo.id_tramite == id_tramite,
        TramiteCampo.clave == clave.strip().lower(),
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_campos_tramite(
    db: Session,
    id_tramite: int,
    *,
    solo_activos: bool = False,
) -> Sequence[TramiteCampo]:
    """
    Lista los campos configurados para un trámite.
    """
    consulta = (
        select(TramiteCampo)
        .where(
            TramiteCampo.id_tramite == id_tramite,
        )
        .order_by(
            TramiteCampo.orden.asc(),
            TramiteCampo.id_campo.asc(),
        )
    )

    if solo_activos:
        consulta = consulta.where(
            TramiteCampo.activo.is_(True)
        )

    return db.scalars(
        consulta
    ).all()


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
    """
    Modifica un campo configurable existente.
    """
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
# ETAPAS CONFIGURABLES
# ============================================================


def crear_etapa(
    db: Session,
    *,
    id_tramite: int,
    id_unidad: int | None,
    nombre: str,
    descripcion: str | None,
    orden: int,
    es_inicial: bool,
    es_final: bool,
    activo: bool,
) -> TramiteEtapa:
    """
    Crea una etapa configurada para un trámite.

    Esta función solamente persiste configuraciones que hayan
    sido definidas explícitamente. No infiere procesos.
    """
    etapa = TramiteEtapa(
        id_tramite=id_tramite,
        id_unidad=id_unidad,
        nombre=nombre,
        descripcion=descripcion,
        orden=orden,
        es_inicial=es_inicial,
        es_final=es_final,
        activo=activo,
    )

    db.add(etapa)
    db.flush()
    db.refresh(etapa)

    return etapa


def obtener_etapa_por_id(
    db: Session,
    id_etapa: int,
) -> TramiteEtapa | None:
    """
    Obtiene una etapa con su unidad asociada.
    """
    consulta = (
        select(TramiteEtapa)
        .where(
            TramiteEtapa.id_etapa == id_etapa,
        )
        .options(
            selectinload(
                TramiteEtapa.unidad,
            ),
        )
    )

    return db.scalars(
        consulta
    ).one_or_none()


def obtener_etapa_por_orden(
    db: Session,
    *,
    id_tramite: int,
    orden: int,
) -> TramiteEtapa | None:
    """
    Busca una etapa por su posición dentro del trámite.
    """
    consulta = select(
        TramiteEtapa
    ).where(
        TramiteEtapa.id_tramite == id_tramite,
        TramiteEtapa.orden == orden,
    )

    return db.scalars(
        consulta
    ).one_or_none()


def listar_etapas_tramite(
    db: Session,
    id_tramite: int,
    *,
    solo_activas: bool = False,
) -> Sequence[TramiteEtapa]:
    """
    Lista las etapas configuradas para un trámite.

    Puede devolver una lista vacía mientras el proceso
    institucional no haya sido configurado.
    """
    consulta = (
        select(TramiteEtapa)
        .where(
            TramiteEtapa.id_tramite == id_tramite,
        )
        .options(
            selectinload(
                TramiteEtapa.unidad,
            ),
        )
        .order_by(
            TramiteEtapa.orden.asc(),
        )
    )

    if solo_activas:
        consulta = consulta.where(
            TramiteEtapa.activo.is_(True)
        )

    return db.scalars(
        consulta
    ).all()


def obtener_etapa_inicial(
    db: Session,
    id_tramite: int,
) -> TramiteEtapa | None:
    """
    Obtiene la etapa inicial activa configurada.

    Puede devolver None si el flujo aún no ha sido confirmado.
    """
    consulta = select(
        TramiteEtapa
    ).where(
        TramiteEtapa.id_tramite == id_tramite,
        TramiteEtapa.es_inicial.is_(True),
        TramiteEtapa.activo.is_(True),
    )

    return db.scalars(
        consulta
    ).one_or_none()


def obtener_etapa_final(
    db: Session,
    id_tramite: int,
) -> TramiteEtapa | None:
    """
    Obtiene la etapa final activa configurada.

    Puede devolver None si el flujo aún no ha sido confirmado.
    """
    consulta = select(
        TramiteEtapa
    ).where(
        TramiteEtapa.id_tramite == id_tramite,
        TramiteEtapa.es_final.is_(True),
        TramiteEtapa.activo.is_(True),
    )

    return db.scalars(
        consulta
    ).one_or_none()


def actualizar_etapa(
    db: Session,
    etapa: TramiteEtapa,
    *,
    id_unidad: int | None = None,
    nombre: str | None = None,
    descripcion: str | None = None,
    orden: int | None = None,
    es_inicial: bool | None = None,
    es_final: bool | None = None,
    activo: bool | None = None,
    actualizar_unidad: bool = False,
    actualizar_descripcion: bool = False,
) -> TramiteEtapa:
    """
    Modifica una etapa configurada existente.
    """
    if actualizar_unidad:
        etapa.id_unidad = id_unidad

    if nombre is not None:
        etapa.nombre = nombre

    if actualizar_descripcion:
        etapa.descripcion = descripcion

    if orden is not None:
        etapa.orden = orden

    if es_inicial is not None:
        etapa.es_inicial = es_inicial

    if es_final is not None:
        etapa.es_final = es_final

    if activo is not None:
        etapa.activo = activo

    db.flush()
    db.refresh(etapa)

    return etapa

def bloquear_configuracion(db: Session, id_tramite: int) -> Tramite | None:
    return db.scalar(select(Tramite).where(Tramite.id_tramite == id_tramite).with_for_update())


def guardar_orden_etapas(db: Session, etapas: list[TramiteEtapa]) -> None:
    # Evita colisiones con la unicidad inmediata (tramite, orden).
    desplazamiento = max(e.orden for e in etapas) + len(etapas) + 1
    for i, etapa in enumerate(etapas):
        etapa.orden = desplazamiento + i
    db.flush()
    for i, etapa in enumerate(etapas, 1):
        etapa.orden = i
    db.flush()
