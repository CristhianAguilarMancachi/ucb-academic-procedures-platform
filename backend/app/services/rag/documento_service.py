"""Administración documental sobre el pipeline RAG y las entidades existentes."""
from datetime import date
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import fitz
from sqlalchemy.orm import Session

from app.core.config import DOCUMENTS_DIR
from app.repositories import documento_repository as repo
from app.repositories.gestion_seguimiento.unidad_repository import obtener_unidad_por_nombre
from app.schemas.documento import (
    DocumentoCrearRequest, DocumentoDetalleResponse, DocumentoResponse,
    ListaDocumentosResponse, VersionCrearRequest, VersionDocumentoResponse,
    VigenciaDocumentoRequest,
)
from app.services.auth.audit_service import registrar_accion_simple
from app.services.rag.ingest import preparar_chunks

MAX_PDF_BYTES = 19 * 1024 * 1024  # Deja margen para multipart bajo client_max_body_size 20M.


class DocumentoError(Exception):
    def __init__(self, mensaje: str, status_code: int = 400):
        super().__init__(mensaje)
        self.status_code = status_code


def archivo_conservado(ruta: str) -> Path | None:
    """Solo archivos regulares dentro del almacén; también comprueba symlinks."""
    try:
        path = Path(ruta).resolve()
        if path.is_relative_to(DOCUMENTS_DIR.resolve()) and path.is_file():
            return path
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def guardar_pdf(archivo: BinaryIO, nombre: str) -> Path:
    if Path(nombre).suffix.lower() != ".pdf":
        raise DocumentoError("Selecciona un archivo PDF.")
    carpeta = DOCUMENTS_DIR.resolve() / "administracion"
    carpeta.mkdir(parents=True, exist_ok=True)
    if not carpeta.resolve().is_relative_to(DOCUMENTS_DIR.resolve()):
        raise DocumentoError("El almacén documental no está disponible.", 503)
    path = carpeta / f"{uuid4().hex}.pdf"
    try:
        total = 0
        with path.open("xb") as destino:
            while bloque := archivo.read(65536):
                total += len(bloque)
                if total > MAX_PDF_BYTES:
                    raise DocumentoError("El PDF no puede superar 19 MiB.", 413)
                destino.write(bloque)
        with path.open("rb") as fuente:
            if total == 0 or not fuente.read(1024).lstrip().startswith(b"%PDF-"):
                raise DocumentoError("El archivo no contiene un PDF válido.")
        with fitz.open(path) as pdf:
            if not pdf.is_pdf or pdf.needs_pass or pdf.page_count < 1:
                raise DocumentoError("El PDF debe tener páginas y no requerir contraseña.")
        return path
    except Exception as exc:
        path.unlink(missing_ok=True)
        if isinstance(exc, DocumentoError):
            raise
        raise DocumentoError("No se pudo leer o conservar el PDF.") from exc


def version_vigente(version, hoy: date | None = None) -> bool:
    hoy = hoy or date.today()
    inicio = version.vigente_desde or version.fecha_version.date()
    return inicio <= hoy and (version.vigente_hasta is None or version.vigente_hasta >= hoy)


def _version_response(version, cantidad: int) -> VersionDocumentoResponse:
    return VersionDocumentoResponse(
        id_version_documento=version.id_version_documento, numero_version=version.numero_version,
        estado=version.estado, fecha_version=version.fecha_version,
        vigente_desde=version.vigente_desde, vigente_hasta=version.vigente_hasta,
        desde_efectivo=version.vigente_desde or version.fecha_version.date(),
        vigente=version_vigente(version), cantidad_chunks=cantidad,
        descargable=archivo_conservado(version.ruta_archivo) is not None, observacion=version.observacion,
    )


def _documento_response(documento, version, cantidades) -> DocumentoResponse:
    actual = _version_response(version, cantidades.get(version.id_version_documento, 0)) if version else None
    return DocumentoResponse(
        id_documento_institucional=documento.id_documento_institucional, titulo=documento.titulo,
        unidad_origen=documento.unidad_origen, descripcion=documento.descripcion, estado=documento.estado,
        fecha_carga=documento.fecha_carga, fecha_actualizacion=documento.fecha_actualizacion,
        id_version_actual=documento.id_version_actual, version_actual=actual,
        utilizable_rag=bool(documento.estado == "activo" and actual and actual.estado == "activo"
                           and actual.vigente and actual.cantidad_chunks > 0),
    )


def listar_documentos(db: Session, pagina: int, por_pagina: int) -> ListaDocumentosResponse:
    documentos, total = repo.listar_documentos(db, pagina, por_pagina)
    cantidades = repo.cantidades_chunks(db, [d.id_version_actual for d in documentos if d.id_version_actual])
    items = []
    for documento in documentos:
        version = documento.version_actual
        if version and version.id_documento_institucional != documento.id_documento_institucional:
            version = None
        items.append(_documento_response(documento, version, cantidades))
    return ListaDocumentosResponse(items=items, total=total, pagina=pagina, por_pagina=por_pagina)


def _documento(db: Session, id_documento: int, *, bloquear=False):
    documento = repo.obtener_documento(db, id_documento, bloquear=bloquear)
    if documento is None:
        raise DocumentoError("Documento no encontrado.", 404)
    return documento


def _version(db: Session, id_documento: int, id_version: int):
    version = repo.obtener_version(db, id_documento, id_version)
    if version is None:
        raise DocumentoError("Versión no encontrada en este documento.", 404)
    return version


def detalle_documento(db: Session, id_documento: int) -> DocumentoDetalleResponse:
    documento = _documento(db, id_documento)
    versiones = repo.listar_versiones(db, id_documento)
    cantidades = repo.cantidades_chunks(db, [v.id_version_documento for v in versiones])
    actual = next((v for v in versiones if v.id_version_documento == documento.id_version_actual), None)
    return DocumentoDetalleResponse(**_documento_response(documento, actual, cantidades).model_dump(),
        versiones=[_version_response(v, cantidades.get(v.id_version_documento, 0)) for v in versiones])


def descargar_version(db: Session, id_documento: int, id_version: int) -> Path:
    version = _version(db, id_documento, id_version)
    path = archivo_conservado(version.ruta_archivo)
    if path is None:
        raise DocumentoError("El archivo de esta versión no está disponible.", 404)
    return path


def _auditar(db: Session, documento, accion: str, actor: int, id_version: int | None = None):
    registrar_accion_simple(db, accion=accion, modulo="documentos", id_usuario_actor=actor,
        entidad="documento_institucional", id_entidad=documento.id_documento_institucional,
        detalle={"id_version_documento": id_version, "estado": documento.estado})


def cargar_documento(db: Session, datos: DocumentoCrearRequest, archivo: BinaryIO, nombre: str, actor: int):
    unidad = obtener_unidad_por_nombre(db, datos.unidad_origen)
    if unidad is None or not unidad.activo:
        raise DocumentoError("Selecciona una unidad administrativa activa existente.")
    path = guardar_pdf(archivo, nombre)
    try:
        file_hash, chunks = preparar_chunks(path)
        documento = repo.crear_documento(db, titulo=datos.titulo, tipo_documento="PDF",
            unidad_origen=unidad.nombre, descripcion=datos.descripcion, estado=datos.estado,
            ruta_archivo=str(path), hash_archivo=file_hash)
        version = repo.crear_version(db, id_documento_institucional=documento.id_documento_institucional,
            numero_version="1", ruta_archivo=str(path), hash_archivo=file_hash, estado="activo",
            vigente_desde=datos.vigente_desde, vigente_hasta=datos.vigente_hasta)
        repo.guardar_chunks(db, version.id_version_documento, chunks)
        repo.establecer_version_actual(db, documento, version)
        _auditar(db, documento, "cargar_documento", actor, version.id_version_documento)
        resultado = detalle_documento(db, documento.id_documento_institucional)
        db.commit()
        return resultado
    except Exception as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        raise DocumentoError("La ingesta no pudo completarse. No se publicó el documento.", 503) from exc


def nueva_version(db: Session, id_documento: int, datos: VersionCrearRequest,
                  archivo: BinaryIO, nombre: str, actor: int):
    _documento(db, id_documento)
    path = guardar_pdf(archivo, nombre)
    try:
        file_hash, chunks = preparar_chunks(path)
        documento = _documento(db, id_documento, bloquear=True)
        version = repo.crear_version(db, id_documento_institucional=id_documento,
            numero_version=repo.siguiente_numero_version(db, id_documento),
            ruta_archivo=str(path), hash_archivo=file_hash, estado="activo", observacion=datos.observacion,
            vigente_desde=datos.vigente_desde, vigente_hasta=datos.vigente_hasta)
        repo.guardar_chunks(db, version.id_version_documento, chunks)
        repo.establecer_version_actual(db, documento, version)
        _auditar(db, documento, "nueva_version_documento", actor, version.id_version_documento)
        resultado = detalle_documento(db, id_documento)
        db.commit()
        return resultado
    except Exception as exc:
        db.rollback()
        path.unlink(missing_ok=True)
        raise DocumentoError("No se pudo publicar la nueva versión. Se conserva la anterior.", 503) from exc


def actualizar_documento(db: Session, id_documento: int, actor: int, *,
                         estado: str | None = None, id_version: int | None = None,
                         vigencia: VigenciaDocumentoRequest | None = None, reingestar: bool = False):
    try:
        documento = _documento(db, id_documento, bloquear=True)
        if estado is not None:
            documento.estado = estado
            accion = "cambiar_estado_documento"
        else:
            version = _version(db, id_documento, id_version)
            if reingestar:
                path = descargar_version(db, id_documento, id_version)
                file_hash, chunks = preparar_chunks(path, repo.modo_version(db, id_version))
                if file_hash != version.hash_archivo:
                    raise DocumentoError("El archivo cambió; cárgalo como una nueva versión.", 409)
                repo.guardar_chunks(db, id_version, chunks, reemplazar=True)
                accion = "reingestar_documento"
            else:
                version.vigente_desde = vigencia.vigente_desde
                version.vigente_hasta = vigencia.vigente_hasta
                accion = "cambiar_vigencia_documento"
        repo.guardar_cambios(db, documento)
        _auditar(db, documento, accion, actor, id_version)
        resultado = detalle_documento(db, id_documento)
        db.commit()
        return resultado
    except Exception as exc:
        db.rollback()
        if isinstance(exc, DocumentoError):
            raise
        raise DocumentoError("No se completó la operación. Se conserva el estado anterior.", 503) from exc
