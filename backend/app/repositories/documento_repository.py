
"""Persistencia de las entidades documentales; sin HTTP ni commits."""

from sqlalchemy import Date, cast, delete, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.archivo_documento import ArchivoDocumento as Archivo
from app.models.documento_institucional import DocumentoInstitucional as Documento
from app.models.version_documento import VersionDocumento as Version
from app.models.chunk_documento import ChunkDocumento as Chunk


def condiciones_version_utilizable():
    # Se conserva la regla actual del RAG.
    return (
        Documento.estado == "activo",
        Documento.id_version_actual == Version.id_version_documento,
        Version.id_documento_institucional
        == Documento.id_documento_institucional,
        Version.estado == "activo",
        func.coalesce(
            Version.vigente_desde,
            cast(Version.fecha_version, Date),
        ) <= func.current_date(),
        or_(
            Version.vigente_hasta.is_(None),
            Version.vigente_hasta >= func.current_date(),
        ),
    )


def listar_documentos(db: Session, pagina: int, por_pagina: int):
    total = db.scalar(
        select(func.count()).select_from(Documento)
    ) or 0

    items = list(
        db.scalars(
            select(Documento)
            .options(selectinload(Documento.version_actual))
            .order_by(
                Documento.fecha_actualizacion.desc(),
                Documento.id_documento_institucional.desc(),
            )
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
    )

    return items, total


def obtener_documento(
    db: Session,
    id_documento: int,
    *,
    bloquear: bool = False,
):
    return db.get(
        Documento,
        id_documento,
        with_for_update=bloquear,
        populate_existing=bloquear,
    )


def obtener_version(
    db: Session,
    id_documento: int,
    id_version: int,
):
    return db.scalar(
        select(Version).where(
            Version.id_documento_institucional == id_documento,
            Version.id_version_documento == id_version,
        )
    )


def listar_versiones(db: Session, id_documento: int):
    return list(
        db.scalars(
            select(Version)
            .where(
                Version.id_documento_institucional == id_documento
            )
            .order_by(
                Version.fecha_version.desc(),
                Version.id_version_documento.desc(),
            )
        )
    )


def cantidades_chunks(
    db: Session,
    ids: list[int],
) -> dict[int, int]:
    if not ids:
        return {}

    return dict(
        db.execute(
            select(
                Chunk.id_version_documento,
                func.count(),
            )
            .where(
                Chunk.id_version_documento.in_(ids),
                Chunk.activo.is_(True),
                Chunk.embedding.is_not(None),
            )
            .group_by(Chunk.id_version_documento)
        ).all()
    )


def ids_archivos_disponibles(
    db: Session,
    ids: list[int],
) -> set[int]:
    """
    Consulta solamente identificadores.

    No recupera el contenido binario de los PDF
    al listar los documentos.
    """
    if not ids:
        return set()

    return set(
        db.scalars(
            select(Archivo.id_version_documento).where(
                Archivo.id_version_documento.in_(ids)
            )
        ).all()
    )


def obtener_archivo_pdf(
    db: Session,
    id_version: int,
) -> bytes | None:
    """
    Recupera el PDF original almacenado en PostgreSQL.
    """
    return db.scalar(
        select(Archivo.contenido_pdf).where(
            Archivo.id_version_documento == id_version
        )
    )


def guardar_archivo_pdf(
    db: Session,
    id_version: int,
    nombre: str,
    contenido: bytes,
):
    """
    Registra el PDF correspondiente a una versión.

    No hace commit: la transacción es responsabilidad
    del servicio documental.
    """
    db.add(
        Archivo(
            id_version_documento=id_version,
            nombre_archivo_original=nombre,
            contenido_pdf=contenido,
        )
    )
    db.flush()


def crear_documento(db: Session, **datos):
    documento = Documento(**datos)
    db.add(documento)
    db.flush()
    return documento


def crear_version(db: Session, **datos):
    version = Version(**datos)
    db.add(version)
    db.flush()
    return version


def siguiente_numero_version(
    db: Session,
    id_documento: int,
) -> str:
    # Compatible con etiquetas históricas no numéricas.
    etiquetas = set(
        db.scalars(
            select(Version.numero_version).where(
                Version.id_documento_institucional
                == id_documento
            )
        )
    )

    numero = 1

    while str(numero) in etiquetas:
        numero += 1

    return str(numero)


def modo_version(
    db: Session,
    id_version: int,
) -> str:
    """Recupera el modo de fragmentación utilizado por una versión."""
    estrategias = set(
        db.scalars(
            select(Chunk.estrategia_chunking)
            .where(
                Chunk.id_version_documento == id_version
            )
            .distinct()
        )
    )

    if "faq_tematico" in estrategias:
        return "faq"

    if "lineamiento" in estrategias:
        return "lineamiento"

    if "general_parrafos" in estrategias:
        return "general"

    return "normativo"



def guardar_chunks(
    db: Session,
    id_version: int,
    chunks: list[dict],
    *,
    reemplazar: bool = False,
):
    if reemplazar:
        db.execute(
            delete(Chunk).where(
                Chunk.id_version_documento == id_version
            )
        )

    db.add_all(
        [
            Chunk(
                id_version_documento=id_version,
                **datos,
            )
            for datos in chunks
        ]
    )

    db.flush()


def establecer_version_actual(
    db: Session,
    documento: Documento,
    version: Version,
):
    documento.id_version_actual = (
        version.id_version_documento
    )
    documento.hash_archivo = version.hash_archivo
    documento.fecha_actualizacion = func.now()

    db.flush()


def guardar_cambios(
    db: Session,
    documento: Documento,
):
    documento.fecha_actualizacion = func.now()
    db.flush()
