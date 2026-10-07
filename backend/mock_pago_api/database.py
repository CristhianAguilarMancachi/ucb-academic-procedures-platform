from __future__ import annotations

import os
import sqlite3

from pathlib import Path
from typing import Any


# ============================================================
# UBICACIÓN DE LA BASE DEL SERVICIO EXTERNO SIMULADO
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent

DEFAULT_DB_PATH = (
    BASE_DIR
    / "data"
    / "mock_pago.db"
)

DB_PATH = Path(
    os.getenv(
        "MOCK_PAGO_DB_PATH",
        str(DEFAULT_DB_PATH),
    )
)


# ============================================================
# CONEXIÓN
# ============================================================


def _crear_directorio() -> None:
    """
    Crea el directorio de la base SQLite si todavía no existe.
    """
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def obtener_conexion() -> sqlite3.Connection:
    """
    Abre una conexión a la base independiente del mock.

    Esta SQLite representa únicamente al sistema externo de
    facturación durante desarrollo.

    No forma parte de la base PostgreSQL de M03.
    """
    _crear_directorio()

    conexion = sqlite3.connect(
        DB_PATH,
    )

    conexion.row_factory = (
        sqlite3.Row
    )

    conexion.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return conexion


# ============================================================
# INICIALIZACIÓN
# ============================================================


def inicializar_base_datos() -> None:
    """
    Prepara la base del sistema externo simulado.

    La estructura conserva las columnas antiguas estado y
    utilizada para mantener compatibilidad con el mock ya
    existente.

    Sin embargo, todas las facturas cargadas aquí representan
    pagos ya procesados:

        estado = pagada
        utilizada = 0

    La reutilización entre solicitudes se controla en M03.
    """
    with obtener_conexion() as conexion:
        conexion.executescript(
            """
            CREATE TABLE IF NOT EXISTS concepto_pago (
                codigo TEXT PRIMARY KEY,

                nombre TEXT NOT NULL,

                monto TEXT NOT NULL,

                moneda TEXT NOT NULL,

                gestion INTEGER NOT NULL,

                activo INTEGER NOT NULL
                    DEFAULT 1
            );


            CREATE TABLE IF NOT EXISTS factura (
                numero_factura TEXT PRIMARY KEY,

                codigo_concepto TEXT NOT NULL,

                monto_pagado TEXT NOT NULL,

                moneda TEXT NOT NULL,

                estado TEXT NOT NULL,

                fecha_emision TEXT NOT NULL,

                fecha_pago TEXT,

                utilizada INTEGER NOT NULL
                    DEFAULT 0,

                FOREIGN KEY (
                    codigo_concepto
                )
                REFERENCES concepto_pago(codigo)
            );
            """
        )

        # La versión anterior del mock no almacenaba el CI.
        # Si la SQLite ya existía, agregamos la columna.
        columnas_factura = {
            fila["name"]
            for fila in conexion.execute(
                "PRAGMA table_info(factura);"
            ).fetchall()
        }

        if (
            "documento_identidad"
            not in columnas_factura
        ):
            conexion.execute(
                """
                ALTER TABLE factura
                ADD COLUMN documento_identidad TEXT;
                """
            )

        conexion.executescript(
            """
            CREATE INDEX IF NOT EXISTS
            idx_factura_documento_identidad
            ON factura(documento_identidad);


            CREATE INDEX IF NOT EXISTS
            idx_factura_codigo_concepto
            ON factura(codigo_concepto);
            """
        )

        # Esta SQLite contiene únicamente información ficticia
        # de desarrollo.
        #
        # Se reinicializan sus datos para eliminar los antiguos
        # FAC-PRUEBA-* y otros escenarios que ya no representan
        # el funcionamiento definido.
        conexion.execute(
            "DELETE FROM factura;"
        )

        conexion.execute(
            "DELETE FROM concepto_pago;"
        )

        _cargar_datos_iniciales(
            conexion
        )


# ============================================================
# DATOS EXTERNOS SIMULADOS
# ============================================================


def _cargar_datos_iniciales(
    conexion: sqlite3.Connection,
) -> None:
    """
    Carga conceptos y facturas ficticias del sistema externo.

    Los códigos MOCK-* son referencias de desarrollo y NO
    representan códigos institucionales oficiales.

    Se mantienen porque actualmente M03 ya utiliza esos códigos
    en su configuración económica.

    Cuando se conozcan los Cod. Servicio reales, estas
    referencias podrán reemplazarse por las oficiales.

    Todas las facturas de esta lista representan pagos ya
    realizados y procesados fuera de M03.
    """

    # ========================================================
    # CATÁLOGO EXTERNO DE SERVICIOS
    # ========================================================
    #
    # Estructura:
    #
    # (
    #     codigo,
    #     nombre,
    #     monto,
    #     moneda,
    #     gestion,
    #     activo,
    # )
    #
    # ========================================================

    conceptos = [
        (
            "MOCK-TITULO-001",
            "Formulario Título Académico",
            "1300.00",
            "BOB",
            2026,
            1,
        ),

        (
            "MOCK-DIPLOMA-001",
            "Diploma Académico",
            "1300.00",
            "BOB",
            2026,
            1,
        ),

        (
            "MOCK-SUPLETORIO-001",
            "Certificado Supletorio",
            "880.00",
            "BOB",
            2026,
            1,
        ),

        (
            "MOCK-LEGALIZACION-001",
            "Legalización Título Académico",
            "110.00",
            "BOB",
            2026,
            1,
        ),

        (
            "MOCK-CERT-CONCLUSION-001",
            "Certificado de Conclusión de Materias",
            "55.00",
            "BOB",
            2026,
            1,
        ),

        (
            "MOCK-CERT-NOTAS-001",
            "Certificado de Notas",
            "55.00",
            "BOB",
            2026,
            1,
        ),

        (
            "MOCK-APOSTILLA-001",
            "Verificación Documentos Exterior/Apostilla",
            "88.00",
            "BOB",
            2026,
            1,
        ),
    ]


    conexion.executemany(
        """
        INSERT INTO concepto_pago (
            codigo,
            nombre,
            monto,
            moneda,
            gestion,
            activo
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        conceptos,
    )


    # ========================================================
    # FACTURAS PROCESADAS
    # ========================================================
    #
    # Se utilizan tres CI ficticios para poder comprobar:
    #
    # - factura correcta para el estudiante;
    # - factura real que pertenece a otra persona;
    # - factura real del mismo estudiante pero de otro servicio.
    #
    # Todas estas facturas representan pagos ya realizados.
    #
    # No tenemos:
    #
    # - factura pendiente;
    # - factura anulada;
    # - factura sin pagar;
    # - FAC-PRUEBA-*.
    #
    # Si el estudiante todavía no pagó, sencillamente no tiene
    # una factura que pueda registrar en M03.
    #
    #
    # Estructura:
    #
    # (
    #     numero_factura,
    #     documento_identidad,
    #     codigo_concepto,
    #     monto_pagado,
    #     moneda,
    #     estado,
    #     fecha_emision,
    #     fecha_pago,
    #     utilizada,
    # )
    #
    # ========================================================

    facturas = [

        # ----------------------------------------------------
        # FORMULARIO TÍTULO ACADÉMICO
        # Cod. Servicio: MOCK-TITULO-001
        # ----------------------------------------------------

        (
            "26010001",
            "1234567",
            "MOCK-TITULO-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-09-01T09:00:00-04:00",
            "2026-09-01T09:04:00-04:00",
            0,
        ),

        (
            "26010002",
            "7654321",
            "MOCK-TITULO-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-09-01T10:00:00-04:00",
            "2026-09-01T10:03:00-04:00",
            0,
        ),

        (
            "26010003",
            "6908010",
            "MOCK-TITULO-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-09-01T11:00:00-04:00",
            "2026-09-01T11:05:00-04:00",
            0,
        ),


        # ----------------------------------------------------
        # DIPLOMA ACADÉMICO
        # Cod. Servicio: MOCK-DIPLOMA-001
        # ----------------------------------------------------

        (
            "26020001",
            "1234567",
            "MOCK-DIPLOMA-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-09-02T09:00:00-04:00",
            "2026-09-02T09:04:00-04:00",
            0,
        ),

        (
            "26020002",
            "7654321",
            "MOCK-DIPLOMA-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-09-02T10:00:00-04:00",
            "2026-09-02T10:03:00-04:00",
            0,
        ),

        (
            "26020003",
            "6908010",
            "MOCK-DIPLOMA-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-09-02T11:00:00-04:00",
            "2026-09-02T11:05:00-04:00",
            0,
        ),


        # ----------------------------------------------------
        # CERTIFICADO SUPLETORIO
        # Cod. Servicio: MOCK-SUPLETORIO-001
        # ----------------------------------------------------

        (
            "26030001",
            "1234567",
            "MOCK-SUPLETORIO-001",
            "880.00",
            "BOB",
            "pagada",
            "2026-09-03T09:00:00-04:00",
            "2026-09-03T09:04:00-04:00",
            0,
        ),

        (
            "26030002",
            "7654321",
            "MOCK-SUPLETORIO-001",
            "880.00",
            "BOB",
            "pagada",
            "2026-09-03T10:00:00-04:00",
            "2026-09-03T10:03:00-04:00",
            0,
        ),

        (
            "26030003",
            "6908010",
            "MOCK-SUPLETORIO-001",
            "880.00",
            "BOB",
            "pagada",
            "2026-09-03T11:00:00-04:00",
            "2026-09-03T11:05:00-04:00",
            0,
        ),


        # ----------------------------------------------------
        # LEGALIZACIÓN TÍTULO ACADÉMICO
        # Cod. Servicio: MOCK-LEGALIZACION-001
        # ----------------------------------------------------

        (
            "26040001",
            "1234567",
            "MOCK-LEGALIZACION-001",
            "110.00",
            "BOB",
            "pagada",
            "2026-09-04T09:00:00-04:00",
            "2026-09-04T09:04:00-04:00",
            0,
        ),

        (
            "26040002",
            "7654321",
            "MOCK-LEGALIZACION-001",
            "110.00",
            "BOB",
            "pagada",
            "2026-09-04T10:00:00-04:00",
            "2026-09-04T10:03:00-04:00",
            0,
        ),

        (
            "26040003",
            "6908010",
            "MOCK-LEGALIZACION-001",
            "110.00",
            "BOB",
            "pagada",
            "2026-09-04T11:00:00-04:00",
            "2026-09-04T11:05:00-04:00",
            0,
        ),


        # ----------------------------------------------------
        # CERTIFICADO DE CONCLUSIÓN DE MATERIAS
        # Cod. Servicio: MOCK-CERT-CONCLUSION-001
        # ----------------------------------------------------

        (
            "26050001",
            "1234567",
            "MOCK-CERT-CONCLUSION-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-09-05T09:00:00-04:00",
            "2026-09-05T09:04:00-04:00",
            0,
        ),

        (
            "26050002",
            "7654321",
            "MOCK-CERT-CONCLUSION-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-09-05T10:00:00-04:00",
            "2026-09-05T10:03:00-04:00",
            0,
        ),

        (
            "26050003",
            "6908010",
            "MOCK-CERT-CONCLUSION-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-09-05T11:00:00-04:00",
            "2026-09-05T11:05:00-04:00",
            0,
        ),


        # ----------------------------------------------------
        # CERTIFICADO DE NOTAS
        # Cod. Servicio: MOCK-CERT-NOTAS-001
        # ----------------------------------------------------

        (
            "26060001",
            "1234567",
            "MOCK-CERT-NOTAS-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-09-06T09:00:00-04:00",
            "2026-09-06T09:04:00-04:00",
            0,
        ),

        (
            "26060002",
            "7654321",
            "MOCK-CERT-NOTAS-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-09-06T10:00:00-04:00",
            "2026-09-06T10:03:00-04:00",
            0,
        ),

        (
            "26060003",
            "6908010",
            "MOCK-CERT-NOTAS-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-09-06T11:00:00-04:00",
            "2026-09-06T11:05:00-04:00",
            0,
        ),


        # ----------------------------------------------------
        # VERIFICACIÓN DOCUMENTOS EXTERIOR / APOSTILLA
        # Cod. Servicio: MOCK-APOSTILLA-001
        # ----------------------------------------------------

        (
            "26070001",
            "1234567",
            "MOCK-APOSTILLA-001",
            "88.00",
            "BOB",
            "pagada",
            "2026-09-07T09:00:00-04:00",
            "2026-09-07T09:04:00-04:00",
            0,
        ),

        (
            "26070002",
            "7654321",
            "MOCK-APOSTILLA-001",
            "88.00",
            "BOB",
            "pagada",
            "2026-09-07T10:00:00-04:00",
            "2026-09-07T10:03:00-04:00",
            0,
        ),

        (
            "26070003",
            "6908010",
            "MOCK-APOSTILLA-001",
            "88.00",
            "BOB",
            "pagada",
            "2026-09-07T11:00:00-04:00",
            "2026-09-07T11:05:00-04:00",
            0,
        ),
    ]


    conexion.executemany(
        """
        INSERT INTO factura (
            numero_factura,
            documento_identidad,
            codigo_concepto,
            monto_pagado,
            moneda,
            estado,
            fecha_emision,
            fecha_pago,
            utilizada
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        facturas,
    )


# ============================================================
# CONSULTAS DEL SISTEMA EXTERNO
# ============================================================


def buscar_factura(
    numero_factura: str,
) -> dict[str, Any] | None:
    """
    Busca una factura por su número y devuelve también los
    datos del concepto económico al que pertenece.

    Esta función no conoce solicitudes ni requisitos de M03.
    """
    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                f.numero_factura,
                f.documento_identidad,
                f.codigo_concepto,
                f.monto_pagado,
                f.moneda,
                f.estado,
                f.fecha_emision,
                f.fecha_pago,
                f.utilizada,

                c.nombre AS nombre_concepto,
                c.monto AS monto_concepto,
                c.moneda AS moneda_concepto,
                c.gestion,
                c.activo

            FROM factura AS f

            INNER JOIN concepto_pago AS c
                ON c.codigo = f.codigo_concepto

            WHERE f.numero_factura = ?;
            """,
            (
                numero_factura,
            ),
        ).fetchone()

    if fila is None:
        return None

    return dict(
        fila
    )


def buscar_concepto(
    codigo: str,
) -> dict[str, Any] | None:
    """
    Busca un Cod. Servicio dentro del catálogo externo.
    """
    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                codigo,
                nombre,
                monto,
                moneda,
                gestion,
                activo

            FROM concepto_pago

            WHERE codigo = ?;
            """,
            (
                codigo,
            ),
        ).fetchone()

    if fila is None:
        return None

    return dict(
        fila
    )