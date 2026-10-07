"""CI para pagos: datos de la solicitud y perfil existente, sin otra entidad."""
from app.repositories.gestion_seguimiento import solicitud_repository, seguimiento_repository


def obtener_documento_pago(db, solicitud):
    # Solo la clave canónica; no se infiere identidad por etiquetas o nombres.
    for dato in solicitud_repository.listar_datos_solicitud(db, solicitud.id_solicitud):
        clave = dato.clave_snapshot or getattr(getattr(dato, 'campo', None), 'clave', None)
        if clave == 'documento_identidad' and isinstance(dato.valor, str) and 3 <= len(dato.valor.strip()) <= 50:
            return dato.valor.strip()
    perfil = seguimiento_repository.obtener_perfil(db, solicitud.id_solicitante)
    documento = (perfil.documento_identidad or '').strip() if perfil else ''
    return documento if 3 <= len(documento) <= 50 else None
