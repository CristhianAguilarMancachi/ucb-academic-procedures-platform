from app.schemas.gestion_seguimiento.pago_verificacion import (
    EstadoPagoVerificacion,
    PagoApiRespuesta,
    PagoApiValidarRequest,
    PagoVerificacionResponse,
    PagoVerificacionResultadoResponse,
)
from app.schemas.gestion_seguimiento.perfil_academico import (
    PerfilAcademicoActualizarRequest,
    PerfilAcademicoResponse,
)
from app.schemas.gestion_seguimiento.solicitud import (
    EstadoSolicitud,
    ListaSolicitudesResponse,
    SolicitudActualizarRequest,
    SolicitudCrearRequest,
    SolicitudDatoGuardarRequest,
    SolicitudDatoResponse,
    SolicitudEnviarRequest,
    SolicitudFacturaGuardarRequest,
    SolicitudRequisitoResponse,
    SolicitudResponse,
    SolicitudResumenResponse,
    TramiteSolicitudResponse,
)
from app.schemas.gestion_seguimiento.solicitud_administrativa import (
    EstadoSolicitudAdministrativa,
    EstadoVerificacionRequisito,
    ListaSolicitudesAdministrativasResponse,
    RequisitoVerificacionResponse,
    RequisitoVerificarRequest,
    SolicitudAdministrativaDetalleResponse,
    SolicitudAdministrativaResumenResponse,
    SolicitudDatoAdministrativoResponse,
    SolicitudRecepcionResponse,
    SolicitudRequisitoAdministrativoResponse,
)
from app.schemas.gestion_seguimiento.tramite import (
    ListaCatalogoTramitesResponse,
    ListaTramitesResponse,
    TramiteActualizarRequest,
    TramiteCatalogoCampoResponse,
    TramiteCatalogoDetalleResponse,
    TramiteCatalogoEconomicoResponse,
    TramiteCatalogoRequisitoResponse,
    TramiteCrearRequest,
    TramiteDetalleResponse,
    TramiteResponse,
    TramiteResumenResponse,
)
from app.schemas.gestion_seguimiento.tramite_campo import (
    TipoDatoCampo,
    TramiteCampoActualizarRequest,
    TramiteCampoCrearRequest,
    TramiteCampoResponse,
)
from app.schemas.gestion_seguimiento.tramite_etapa import (
    TramiteEtapaActualizarRequest,
    TramiteEtapaCrearRequest,
    TramiteEtapaResponse,
)
from app.schemas.gestion_seguimiento.tramite_requisito import (
    RequisitoEconomicoActualizarRequest,
    RequisitoEconomicoCrearRequest,
    RequisitoEconomicoResponse,
    TramiteRequisitoActualizarRequest,
    TramiteRequisitoCrearRequest,
    TramiteRequisitoResponse,
)
from app.schemas.gestion_seguimiento.unidad import (
    ListaUnidadesResponse,
    UnidadActualizarRequest,
    UnidadCrearRequest,
    UnidadDetalleResponse,
    UnidadResponse,
    UsuarioUnidadAsignarRequest,
    UsuarioUnidadResponse,
)


__all__ = [
    # Unidades
    "UnidadCrearRequest",
    "UnidadActualizarRequest",
    "UnidadResponse",
    "UnidadDetalleResponse",
    "ListaUnidadesResponse",
    "UsuarioUnidadAsignarRequest",
    "UsuarioUnidadResponse",

    # Trámites
    "TramiteCrearRequest",
    "TramiteActualizarRequest",
    "TramiteResumenResponse",
    "TramiteResponse",
    "TramiteDetalleResponse",
    "ListaTramitesResponse",
    "ListaCatalogoTramitesResponse",

    # Catálogo público de trámites
    "TramiteCatalogoEconomicoResponse",
    "TramiteCatalogoRequisitoResponse",
    "TramiteCatalogoCampoResponse",
    "TramiteCatalogoDetalleResponse",

    # Requisitos
    "TramiteRequisitoCrearRequest",
    "TramiteRequisitoActualizarRequest",
    "TramiteRequisitoResponse",

    # Configuración económica
    "RequisitoEconomicoCrearRequest",
    "RequisitoEconomicoActualizarRequest",
    "RequisitoEconomicoResponse",

    # Campos configurables
    "TipoDatoCampo",
    "TramiteCampoCrearRequest",
    "TramiteCampoActualizarRequest",
    "TramiteCampoResponse",

    # Etapas
    "TramiteEtapaCrearRequest",
    "TramiteEtapaActualizarRequest",
    "TramiteEtapaResponse",

    # Perfil académico
    "PerfilAcademicoActualizarRequest",
    "PerfilAcademicoResponse",

    # Solicitudes
    "EstadoSolicitud",
    "SolicitudCrearRequest",
    "SolicitudActualizarRequest",
    "SolicitudEnviarRequest",
    "SolicitudFacturaGuardarRequest",
    "SolicitudResumenResponse",
    "SolicitudResponse",
    "ListaSolicitudesResponse",
    "TramiteSolicitudResponse",

    # Datos de solicitud
    "SolicitudDatoGuardarRequest",
    "SolicitudDatoResponse",

    # Requisitos de solicitud
    "SolicitudRequisitoResponse",

    # Gestión administrativa de solicitudes
    "EstadoSolicitudAdministrativa",
    "EstadoVerificacionRequisito",
    "SolicitudAdministrativaResumenResponse",
    "ListaSolicitudesAdministrativasResponse",
    "SolicitudAdministrativaDetalleResponse",
    "SolicitudDatoAdministrativoResponse",
    "SolicitudRequisitoAdministrativoResponse",
    "SolicitudRecepcionResponse",
    "RequisitoVerificarRequest",
    "RequisitoVerificacionResponse",

    # Verificación de pagos
    "EstadoPagoVerificacion",
    "PagoApiValidarRequest",
    "PagoApiRespuesta",
    "PagoVerificacionResponse",
    "PagoVerificacionResultadoResponse",
]