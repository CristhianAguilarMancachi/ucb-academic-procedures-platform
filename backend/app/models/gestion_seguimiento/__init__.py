from app.models.gestion_seguimiento.perfil_academico import (
    PerfilAcademico,
)
from app.models.gestion_seguimiento.solicitud import Solicitud
from app.models.gestion_seguimiento.solicitud_dato import SolicitudDato
from app.models.gestion_seguimiento.solicitud_pago_verificacion import (
    SolicitudPagoVerificacion,
)
from app.models.gestion_seguimiento.solicitud_recepcion import (
    SolicitudRecepcion,
)
from app.models.gestion_seguimiento.solicitud_requisito import (
    SolicitudRequisito,
)
from app.models.gestion_seguimiento.tramite import Tramite
from app.models.gestion_seguimiento.tramite_campo import TramiteCampo
from app.models.gestion_seguimiento.tramite_etapa import TramiteEtapa
from app.models.gestion_seguimiento.tramite_requisito import (
    TramiteRequisito,
)
from app.models.gestion_seguimiento.tramite_requisito_economico import (
    TramiteRequisitoEconomico,
)
from app.models.gestion_seguimiento.unidad_administrativa import (
    UnidadAdministrativa,
)
from app.models.gestion_seguimiento.usuario_unidad import UsuarioUnidad


__all__ = [
    "UnidadAdministrativa",
    "UsuarioUnidad",
    "Tramite",
    "TramiteRequisito",
    "TramiteRequisitoEconomico",
    "TramiteCampo",
    "TramiteEtapa",
    "PerfilAcademico",
    "Solicitud",
    "SolicitudDato",
    "SolicitudRequisito",
    "SolicitudRecepcion",
    "SolicitudPagoVerificacion",
]
from app.models.gestion_seguimiento.solicitud_etapa import SolicitudEtapa
from app.models.gestion_seguimiento.solicitud_historial import SolicitudHistorial
from app.models.gestion_seguimiento.solicitud_observacion import SolicitudObservacion
from app.models.gestion_seguimiento.solicitud_resultado import SolicitudResultado
from app.models.gestion_seguimiento.solicitud_entrega import SolicitudEntrega

__all__ += ['SolicitudEtapa', 'SolicitudHistorial', 'SolicitudObservacion', 'SolicitudResultado', 'SolicitudEntrega']
