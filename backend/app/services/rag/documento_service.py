from datetime import date
from hashlib import sha256
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from uuid import uuid4

import fitz
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import DOCUMENTS_DIR
from app.repositories import documento_repository as repo
from app.repositories.gestion_seguimiento.unidad_repository import (
    obtener_unidad_por_nombre,
)
from app.schemas.documento import (
    DocumentoCrearRequest,
    DocumentoDetalleResponse,
    DocumentoResponse,
    ListaDocumentosResponse,
    VersionCrearRequest,
    VersionDocumentoResponse,
    VigenciaDocumentoRequest,
)
from app.services.auth.audit_service import registrar_accion_simple
from app.services.rag.ingest import preparar_chunks


logger = logging.getLogger(__name__)


MAX_PDF_BYTES = 19 * 1024 * 1024


class DocumentoError(Exception):
    def __init__(
        self,
        mensaje: str,
        status_code: int = 400,
    ):
        super().__init__(mensaje)
        self.status_code = status_code


def _nombre_original(nombre: str) -> str:
    seguro = Path(nombre.replace("\\", "/")).name.strip()

    if (
        not seguro
        or len(seguro) > 255
        or Path(seguro).suffix.lower() != ".pdf"
    ):
        raise DocumentoError(
            "Selecciona un PDF con un nombre válido "
            "de hasta 255 caracteres."
        )

    return seguro


def guardar_pdf(archivo: BinaryIO, nombre: str) -> Path:
    """
    Guarda temporalmente un PDF para validarlo
    y procesarlo con PyMuPDF.

    Este archivo no constituye almacenamiento
    permanente y se elimina al terminar la carga.
    """
    _nombre_original(nombre)

    carpeta = DOCUMENTS_DIR.resolve() / "administracion"
    carpeta.mkdir(parents=True, exist_ok=True)

    if not carpeta.resolve().is_relative_to(
        DOCUMENTS_DIR.resolve()
    ):
        raise DocumentoError(
            "No está disponible el directorio temporal.",
            503,
        )

    path = carpeta / f"{uuid4().hex}.pdf"

    try:
        total = 0

        with path.open("xb") as destino:
            while bloque := archivo.read(65536):
                total += len(bloque)

                if total > MAX_PDF_BYTES:
                    raise DocumentoError(
                        "El PDF no puede superar 19 MiB.",
                        413,
                    )

                destino.write(bloque)

        with path.open("rb") as fuente:
            if (
                total == 0
                or not fuente.read(1024)
                .lstrip()
                .startswith(b"%PDF-")
            ):
                raise DocumentoError(
                    "El archivo no contiene un PDF válido."
                )

        with fitz.open(path) as pdf:
            if (
                not pdf.is_pdf
                or pdf.needs_pass
                or pdf.page_count < 1
            ):
                raise DocumentoError(
                    "El PDF debe tener páginas y "
                    "no requerir contraseña."
                )

        return path

    except Exception as exc:
        path.unlink(missing_ok=True)

        if isinstance(exc, DocumentoError):
            raise

        raise DocumentoError(
            "No se pudo procesar el PDF."
        ) from exc


def _leer_pdf(db: Session, version) -> bytes:
    """
    PostgreSQL es la única fuente permanente
    de archivos PDF.

    No consulta rutas físicas ni carpetas locales.
    """
    contenido = repo.obtener_archivo_pdf(
        db,
        version.id_version_documento,
    )

    if contenido is None:
        raise DocumentoError(
            "El PDF de esta versión no está "
            "almacenado en PostgreSQL.",
            404,
        )

    if sha256(contenido).hexdigest() != (
        version.hash_archivo or ""
    ).lower():
        raise DocumentoError(
            "El PDF almacenado no coincide con "
            "la versión registrada.",
            409,
        )

    return contenido


def _fecha_actual_bd(db: Session) -> date:
    """Misma fecha que utiliza PostgreSQL para el RAG."""
    return db.scalar(select(func.current_date()))


def _inicio_publicacion(db: Session, inicio: date) -> date:
    hoy = _fecha_actual_bd(db)

    if inicio > hoy:
        raise DocumentoError(
            "No se puede publicar una version con "
            "fecha de inicio futura. Publicala "
            "cuando corresponda.",
            422,
        )

    return inicio


def _cerrar_version_anterior(
    db: Session,
    documento,
    fecha_sustitucion: date,
):
    """Finaliza el uso de la version actual anterior."""
    id_anterior = documento.id_version_actual

    if id_anterior is None:
        return

    anterior = repo.obtener_version(
        db,
        documento.id_documento_institucional,
        id_anterior,
    )

    if anterior is None:
        raise DocumentoError(
            "No se encontro la version actual anterior.",
            409,
        )

    inicio_anterior = (
        anterior.vigente_desde
        or anterior.fecha_version.date()
    )

    if inicio_anterior > fecha_sustitucion:
        raise DocumentoError(
            "La version anterior tiene un inicio "
            "posterior a la fecha de sustitucion.",
            409,
        )

    anterior.vigente_hasta = fecha_sustitucion
    db.flush()


def version_vigente(
    version,
    hoy: date | None = None,
) -> bool:
    hoy = hoy or date.today()

    inicio = (
        version.vigente_desde
        or version.fecha_version.date()
    )

    return inicio <= hoy and (
        version.vigente_hasta is None
        or version.vigente_hasta >= hoy
    )


def _version_response(
    version,
    cantidad: int,
    ids_archivos: set[int],
) -> VersionDocumentoResponse:
    return VersionDocumentoResponse(
        id_version_documento=version.id_version_documento,
        numero_version=version.numero_version,
        estado=version.estado,
        fecha_version=version.fecha_version,
        vigente_desde=version.vigente_desde,
        vigente_hasta=version.vigente_hasta,
        desde_efectivo=(
            version.vigente_desde
            or version.fecha_version.date()
        ),
        vigente=version_vigente(version),
        cantidad_chunks=cantidad,
        descargable=(
            version.id_version_documento in ids_archivos
        ),
        observacion=version.observacion,
    )


def _documento_response(
    documento,
    version,
    cantidades,
    ids_archivos,
) -> DocumentoResponse:
    actual = None

    if version is not None:
        actual = _version_response(
            version,
            cantidades.get(
                version.id_version_documento,
                0,
            ),
            ids_archivos,
        )

    return DocumentoResponse(
        id_documento_institucional=(
            documento.id_documento_institucional
        ),
        titulo=documento.titulo,
        unidad_origen=documento.unidad_origen,
        descripcion=documento.descripcion,
        estado=documento.estado,
        fecha_carga=documento.fecha_carga,
        fecha_actualizacion=documento.fecha_actualizacion,
        id_version_actual=documento.id_version_actual,
        version_actual=actual,
        utilizable_rag=bool(
            documento.estado == "activo"
            and actual
            and actual.estado == "activo"
            and actual.vigente
            and actual.cantidad_chunks > 0
        ),
    )


def listar_documentos(
    db: Session,
    pagina: int,
    por_pagina: int,
) -> ListaDocumentosResponse:
    documentos, total = repo.listar_documentos(
        db,
        pagina,
        por_pagina,
    )

    ids = [
        d.id_version_actual
        for d in documentos
        if d.id_version_actual is not None
    ]

    cantidades = repo.cantidades_chunks(db, ids)
    ids_archivos = repo.ids_archivos_disponibles(
        db, ids
    )

    items = []

    for documento in documentos:
        version = documento.version_actual

        if (
            version is not None
            and version.id_documento_institucional
            != documento.id_documento_institucional
        ):
            version = None

        items.append(
            _documento_response(
                documento,
                version,
                cantidades,
                ids_archivos,
            )
        )

    return ListaDocumentosResponse(
        items=items,
        total=total,
        pagina=pagina,
        por_pagina=por_pagina,
    )


def _documento(
    db: Session,
    id_documento: int,
    *,
    bloquear: bool = False,
):
    documento = repo.obtener_documento(
        db,
        id_documento,
        bloquear=bloquear,
    )

    if documento is None:
        raise DocumentoError(
            "Documento no encontrado.",
            404,
        )

    return documento


def _version(
    db: Session,
    id_documento: int,
    id_version: int,
):
    version = repo.obtener_version(
        db,
        id_documento,
        id_version,
    )

    if version is None:
        raise DocumentoError(
            "Versión no encontrada en este documento.",
            404,
        )

    return version


def detalle_documento(
    db: Session,
    id_documento: int,
) -> DocumentoDetalleResponse:
    documento = _documento(db, id_documento)

    versiones = repo.listar_versiones(
        db, id_documento
    )

    ids = [
        v.id_version_documento
        for v in versiones
    ]

    cantidades = repo.cantidades_chunks(db, ids)
    ids_archivos = repo.ids_archivos_disponibles(
        db, ids
    )

    actual = next(
        (
            v
            for v in versiones
            if v.id_version_documento
            == documento.id_version_actual
        ),
        None,
    )

    datos = _documento_response(
        documento,
        actual,
        cantidades,
        ids_archivos,
    ).model_dump()

    respuestas = [
        _version_response(
            v,
            cantidades.get(
                v.id_version_documento,
                0,
            ),
            ids_archivos,
        )
        for v in versiones
    ]

    return DocumentoDetalleResponse(
        **datos,
        versiones=respuestas,
    )


def descargar_version(
    db: Session,
    id_documento: int,
    id_version: int,
) -> bytes:
    version = _version(
        db,
        id_documento,
        id_version,
    )
    return _leer_pdf(db, version)


def _auditar(
    db: Session,
    documento,
    accion: str,
    actor: int,
    id_version: int | None = None,
):
    registrar_accion_simple(
        db,
        accion=accion,
        modulo="documentos",
        id_usuario_actor=actor,
        entidad="documento_institucional",
        id_entidad=documento.id_documento_institucional,
        detalle={
            "id_version_documento": id_version,
            "estado": documento.estado,
        },
    )


def cargar_documento(
    db: Session,
    datos: DocumentoCrearRequest,
    archivo: BinaryIO,
    nombre: str,
    actor: int,
):
    unidad = obtener_unidad_por_nombre(
        db,
        datos.unidad_origen,
    )

    if unidad is None or not unidad.activo:
        raise DocumentoError(
            "Selecciona una unidad administrativa "
            "activa existente."
        )

    inicio_uso = _inicio_publicacion(
        db, datos.vigente_desde
    )
    nombre_original = _nombre_original(nombre)
    path = guardar_pdf(archivo, nombre)

    try:
        file_hash, chunks = preparar_chunks(path)
        contenido = path.read_bytes()

        if sha256(contenido).hexdigest() != file_hash:
            raise DocumentoError(
                "El PDF cambió durante la ingesta.",
                409,
            )

        documento = repo.crear_documento(
            db,
            titulo=datos.titulo,
            tipo_documento="PDF",
            unidad_origen=unidad.nombre,
            descripcion=datos.descripcion,
            estado=datos.estado,
            hash_archivo=file_hash,
        )

        version = repo.crear_version(
            db,
            id_documento_institucional=(
                documento.id_documento_institucional
            ),
            numero_version="1",
            hash_archivo=file_hash,
            estado="activo",
            vigente_desde=inicio_uso,
            vigente_hasta=None,
        )

        repo.guardar_archivo_pdf(
            db,
            version.id_version_documento,
            nombre_original,
            contenido,
        )


        repo.guardar_chunks(
            db,
            version.id_version_documento,
            chunks,
        )

        repo.establecer_version_actual(
            db, documento, version
        )

        _auditar(
            db,
            documento,
            "cargar_documento",
            actor,
            version.id_version_documento,
        )

        resultado = detalle_documento(
            db,
            documento.id_documento_institucional,
        )

        db.commit()
        return resultado

    except Exception as exc:
        db.rollback()

        logger.exception(
            "Fallo durante la carga del documento institucional"
        )

        if isinstance(exc, DocumentoError):
            raise

        raise DocumentoError(
            "La ingesta no pudo completarse. "
            "No se publicó el documento.",
            503,
        ) from exc

    finally:
        path.unlink(missing_ok=True)


def nueva_version(
    db: Session,
    id_documento: int,
    datos: VersionCrearRequest,
    archivo: BinaryIO,
    nombre: str,
    actor: int,
):
    _documento(db, id_documento)
    inicio_uso = _inicio_publicacion(
        db, datos.vigente_desde
    )
    nombre_original = _nombre_original(nombre)
    path = guardar_pdf(archivo, nombre)

    try:
        file_hash, chunks = preparar_chunks(path)
        contenido = path.read_bytes()

        if sha256(contenido).hexdigest() != file_hash:
            raise DocumentoError(
                "El PDF cambió durante la ingesta.",
                409,
            )

        documento = _documento(
            db, id_documento, bloquear=True
        )

        _cerrar_version_anterior(
            db,
            documento,
            _fecha_actual_bd(db),
        )

        version = repo.crear_version(
            db,
            id_documento_institucional=id_documento,
            numero_version=repo.siguiente_numero_version(
                db, id_documento
            ),
            hash_archivo=file_hash,
            estado="activo",
            observacion=datos.observacion,
            vigente_desde=inicio_uso,
            vigente_hasta=None,
        )

        repo.guardar_archivo_pdf(
            db,
            version.id_version_documento,
            nombre_original,
            contenido,
        )


        repo.guardar_chunks(
            db,
            version.id_version_documento,
            chunks,
        )

        repo.establecer_version_actual(
            db, documento, version
        )

        _auditar(
            db,
            documento,
            "nueva_version_documento",
            actor,
            version.id_version_documento,
        )

        resultado = detalle_documento(
            db, id_documento
        )

        db.commit()
        return resultado

    except Exception as exc:
        db.rollback()

        if isinstance(exc, DocumentoError):
            raise

        raise DocumentoError(
            "No se pudo publicar la nueva versión. "
            "Se conserva la anterior.",
            503,
        ) from exc

    finally:
        path.unlink(missing_ok=True)


def actualizar_documento(
    db: Session,
    id_documento: int,
    actor: int,
    *,
    estado: str | None = None,
    id_version: int | None = None,
    vigencia: VigenciaDocumentoRequest | None = None,
    reingestar: bool = False,
):
    try:
        documento = _documento(
            db, id_documento, bloquear=True
        )

        if estado is not None:
            documento.estado = estado
            accion = "cambiar_estado_documento"

        else:
            version = _version(
                db, id_documento, id_version
            )

            if reingestar:
                contenido = _leer_pdf(db, version)

                DOCUMENTS_DIR.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                temporal = None

                try:
                    with NamedTemporaryFile(
                        mode="wb",
                        prefix="rag_reingesta_",
                        suffix=".pdf",
                        dir=DOCUMENTS_DIR,
                        delete=False,
                    ) as fuente:
                        fuente.write(contenido)
                        temporal = Path(fuente.name)

                    file_hash, chunks = preparar_chunks(
                        temporal,
                        repo.modo_version(
                            db, id_version
                        ),
                    )

                    if file_hash != version.hash_archivo:
                        raise DocumentoError(
                            "El PDF cambió durante "
                            "la reingesta.",
                            409,
                        )

                    repo.guardar_chunks(
                        db,
                        id_version,
                        chunks,
                        reemplazar=True,
                    )

                finally:
                    if temporal is not None:
                        temporal.unlink(
                            missing_ok=True
                        )

                accion = "reingestar_documento"

            else:
                if vigencia is None:
                    raise DocumentoError(
                        "Debes proporcionar "
                        "la fecha de vigencia."
                    )

                if (
                    version.id_version_documento
                    != documento.id_version_actual
                ):
                    raise DocumentoError(
                        "Solo puede editarse el inicio de uso "
                        "de la versión actual.",
                        409,
                    )

                if vigencia.vigente_hasta is not None:
                    raise DocumentoError(
                        "La fecha final de uso se registra "
                        "automáticamente al sustituir la versión.",
                        422,
                    )

                version.vigente_desde = _inicio_publicacion(
                    db,
                    vigencia.vigente_desde,
                )
                version.vigente_hasta = None
                accion = "cambiar_vigencia_documento"

        repo.guardar_cambios(db, documento)

        _auditar(
            db,
            documento,
            accion,
            actor,
            id_version,
        )

        resultado = detalle_documento(
            db, id_documento
        )

        db.commit()
        return resultado

    except Exception as exc:
        db.rollback()

        if isinstance(exc, DocumentoError):
            raise

        raise DocumentoError(
            "No se completó la operación. "
            "Se conserva el estado anterior.",
            503,
        ) from exc
