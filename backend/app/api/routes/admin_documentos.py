
from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import Response
from pydantic import ValidationError

from app.core.dependencies import (
    AdministradorActual,
    DatabaseSession,
)
from app.schemas.documento import (
    DocumentoCrearRequest,
    DocumentoDetalleResponse,
    DocumentoEstadoRequest,
    ListaDocumentosResponse,
    VersionCrearRequest,
    VigenciaDocumentoRequest,
)
from app.services.rag import documento_service as servicio


router = APIRouter(
    prefix="/admin/documentos",
    tags=["Administración documental"],
)


def _ejecutar(funcion, *args, **kwargs):
    try:
        return funcion(*args, **kwargs)

    except servicio.DocumentoError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc


def _datos_upload(schema, datos: str):
    try:
        return schema.model_validate_json(datos)

    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Revisa los datos requeridos "
                "y el período de vigencia."
            ),
        ) from exc


@router.get(
    "",
    response_model=ListaDocumentosResponse,
)
def listar(
    administrador: AdministradorActual,
    db: DatabaseSession,
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(20, ge=1, le=100),
):
    return servicio.listar_documentos(
        db,
        pagina,
        por_pagina,
    )


@router.post(
    "",
    response_model=DocumentoDetalleResponse,
    status_code=201,
)
def cargar(
    administrador: AdministradorActual,
    db: DatabaseSession,
    datos: str = Form(...),
    archivo: UploadFile = File(...),
):
    return _ejecutar(
        servicio.cargar_documento,
        db,
        _datos_upload(
            DocumentoCrearRequest,
            datos,
        ),
        archivo.file,
        archivo.filename or "",
        administrador.id_usuario,
    )


@router.get(
    "/{id_documento}",
    response_model=DocumentoDetalleResponse,
)
def detalle(
    id_documento: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
):
    return _ejecutar(
        servicio.detalle_documento,
        db,
        id_documento,
    )


@router.post(
    "/{id_documento}/versiones",
    response_model=DocumentoDetalleResponse,
    status_code=201,
)
def version(
    id_documento: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
    datos: str = Form(...),
    archivo: UploadFile = File(...),
):
    return _ejecutar(
        servicio.nueva_version,
        db,
        id_documento,
        _datos_upload(
            VersionCrearRequest,
            datos,
        ),
        archivo.file,
        archivo.filename or "",
        administrador.id_usuario,
    )


@router.get(
    "/{id_documento}/versiones/{id_version}/archivo"
)
def descargar(
    id_documento: int,
    id_version: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
):
    contenido = _ejecutar(
        servicio.descargar_version,
        db,
        id_documento,
        id_version,
    )

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; "
                f'filename="documento-{id_documento}'
                f'-v{id_version}.pdf"'
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/{id_documento}/estado",
    response_model=DocumentoDetalleResponse,
)
def estado(
    id_documento: int,
    datos: DocumentoEstadoRequest,
    administrador: AdministradorActual,
    db: DatabaseSession,
):
    return _ejecutar(
        servicio.actualizar_documento,
        db,
        id_documento,
        administrador.id_usuario,
        estado=datos.estado,
    )


@router.patch(
    "/{id_documento}/versiones/{id_version}/vigencia",
    response_model=DocumentoDetalleResponse,
)
def vigencia(
    id_documento: int,
    id_version: int,
    datos: VigenciaDocumentoRequest,
    administrador: AdministradorActual,
    db: DatabaseSession,
):
    return _ejecutar(
        servicio.actualizar_documento,
        db,
        id_documento,
        administrador.id_usuario,
        id_version=id_version,
        vigencia=datos,
    )


@router.post(
    "/{id_documento}/versiones/{id_version}/reingestar",
    response_model=DocumentoDetalleResponse,
)
def reingestar(
    id_documento: int,
    id_version: int,
    administrador: AdministradorActual,
    db: DatabaseSession,
):
    return _ejecutar(
        servicio.actualizar_documento,
        db,
        id_documento,
        administrador.id_usuario,
        id_version=id_version,
        reingestar=True,
    )
