"""Facturas ficticias completas: no requieren migrar ni poblar SQLite.

Contrato base: codigo MOCK-CERT-CONCLUSION-001, CI 1234567, 55.00 BOB.
FAC-PRUEBA-INEXISTENTE nunca existe; FAC-PRUEBA-ERROR simula HTTP 503.
Una consulta no consume facturas: M03 controla su acreditación e idempotencia.
"""

BASE = dict(codigo_concepto='MOCK-CERT-CONCLUSION-001', documento_identidad='1234567',
            monto_pagado='55.00', moneda='BOB', estado='pagada', utilizada=False,
            monto_concepto='55.00', moneda_concepto='BOB', activo=True)

CASOS = {
    'FAC-PRUEBA-VALIDA': {},
    'FAC-PRUEBA-CI': {'documento_identidad': '7654321'},
    'FAC-PRUEBA-CODIGO': {'codigo_concepto': 'MOCK-CERT-NOTAS-001'},
    'FAC-PRUEBA-MONTO': {'monto_pagado': '50.00'},
    'FAC-PRUEBA-MONEDA': {'moneda': 'USD'},
    'FAC-PRUEBA-PENDIENTE': {'estado': 'pendiente'},
    'FAC-PRUEBA-UTILIZADA': {'utilizada': True},
}


def buscar_caso(numero_factura):
    if numero_factura not in CASOS:
        return None
    return {**BASE, **CASOS[numero_factura], 'numero_factura': numero_factura}
