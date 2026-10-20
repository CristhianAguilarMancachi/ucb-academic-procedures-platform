
from __future__ import annotations

import os
import sqlite3

from pathlib import Path
from typing import Any


# ============================================================
# UBICACIÓN DE LA BASE DEL SIMULADOR
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

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
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def obtener_conexion() -> sqlite3.Connection:
    """
    SQLite independiente de PostgreSQL.

    Simula únicamente el sistema externo de facturación.
    """
    _crear_directorio()

    conexion = sqlite3.connect(
        DB_PATH
    )

    conexion.row_factory = sqlite3.Row

    conexion.execute(
        "PRAGMA foreign_keys = ON;"
    )

    return conexion


# ============================================================
# CATÁLOGO DE CONCEPTOS ECONÓMICOS
# ============================================================

# Estructura:
# codigo, nombre, monto, moneda, gestion, activo

CONCEPTOS = [
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


# ============================================================
# ESTUDIANTES DE PRUEBA
# ============================================================

# Cinco facturas por estudiante y por concepto.
# Estos CI se utilizan exclusivamente como datos de prueba.

ESTUDIANTES_PRUEBA = [
    "6908410",
    "4369640",
]

FACTURAS_POR_CONCEPTO = 5


# ============================================================
# GENERACIÓN DE FACTURAS
# ============================================================

def _generar_facturas_iniciales() -> list[tuple]:
    """
    Construye las facturas ficticias del simulador.

    Conserva las 21 facturas originales asociadas a:
        1234567
        7654321
        6908010

    Agrega 70 nuevas:
        CI 6908410: 35 facturas
        CI 4369640: 35 facturas

    Cada factura representa un pago ya realizado
    fuera del Sistema de Trámites Académicos.

    No se realizan cobros desde esta aplicación.
    """

    facturas: list[tuple] = []

    # --------------------------------------------------------
    # FACTURAS ANTERIORES
    # --------------------------------------------------------

    estudiantes_anteriores = [
        "1234567",
        "7654321",
        "6908010",
    ]

    minutos_pago_anteriores = [
        4,
        3,
        5,
    ]

    for indice_concepto, concepto in enumerate(
        CONCEPTOS,
        start=1,
    ):
        codigo = concepto[0]
        monto = concepto[2]
        moneda = concepto[3]

        for indice_estudiante, ci in enumerate(
            estudiantes_anteriores,
            start=1,
        ):
            # Se conservan exactamente los números antiguos:
            # 26010001, 26010002, 26010003...
            numero = (
                f"26"
                f"{indice_concepto:02d}"
                f"000"
                f"{indice_estudiante}"
            )

            hora = 8 + indice_estudiante

            fecha_emision = (
                f"2026-09-{indice_concepto:02d}"
                f"T{hora:02d}:00:00-04:00"
            )

            fecha_pago = (
                f"2026-09-{indice_concepto:02d}"
                f"T{hora:02d}:"
                f"{minutos_pago_anteriores[indice_estudiante - 1]:02d}"
                f":00-04:00"
            )

            facturas.append(
                (
                    numero,
                    ci,
                    codigo,
                    monto,
                    moneda,
                    "pagada",
                    fecha_emision,
                    fecha_pago,
                    0,
                )
            )

    # --------------------------------------------------------
    # NUEVAS FACTURAS DE LOS DOS ESTUDIANTES
    # --------------------------------------------------------

    for indice_concepto, concepto in enumerate(
        CONCEPTOS,
        start=1,
    ):
        codigo = concepto[0]
        monto = concepto[2]
        moneda = concepto[3]

        for indice_estudiante, ci in enumerate(
            ESTUDIANTES_PRUEBA,
            start=1,
        ):
            for correlativo in range(
                1,
                FACTURAS_POR_CONCEPTO + 1,
            ):
                # Formato:
                # 26 + concepto(2) + estudiante(2)
                #    + correlativo(2)
                #
                # Ejemplo:
                # 26010101 = título, estudiante 1,
                #            primera factura
                #
                # 26010201 = título, estudiante 2,
                #            primera factura

                numero = (
                    f"26"
                    f"{indice_concepto:02d}"
                    f"{indice_estudiante:02d}"
                    f"{correlativo:02d}"
                )

                hora = 8 + correlativo

                fecha_emision = (
                    "2026-10-19"
                    f"T{hora:02d}:00:00-04:00"
                )

                fecha_pago = (
                    "2026-10-19"
                    f"T{hora:02d}:05:00-04:00"
                )

                facturas.append(
                    (
                        numero,
                        ci,
                        codigo,
                        monto,
                        moneda,
                        "pagada",
                        fecha_emision,
                        fecha_pago,
                        0,
                    )
                )

    # Comprobación interna de unicidad.
    numeros = [
        factura[0]
        for factura in facturas
    ]

    if len(numeros) != len(set(numeros)):
        raise RuntimeError(
            "Se generaron números de factura duplicados."
        )

    return facturas


# ============================================================
# INICIALIZACIÓN DE SQLITE
# ============================================================

def inicializar_base_datos() -> None:
    """
    Crea y carga la base del sistema de pagos simulado.

    La base se reinicializa con datos ficticios al arrancar
    el servicio.

    La utilización real de una factura por una solicitud
    se controla en el backend principal, no aquí.
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
                activo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS factura (
                numero_factura TEXT PRIMARY KEY,
                codigo_concepto TEXT NOT NULL,
                monto_pagado TEXT NOT NULL,
                moneda TEXT NOT NULL,
                estado TEXT NOT NULL,
                fecha_emision TEXT NOT NULL,
                fecha_pago TEXT,
                utilizada INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (codigo_concepto)
                    REFERENCES concepto_pago(codigo)
            );
            """
        )

        # Compatibilidad con versiones anteriores del mock.
        columnas = {
            fila["name"]
            for fila in conexion.execute(
                "PRAGMA table_info(factura);"
            ).fetchall()
        }

        if "documento_identidad" not in columnas:
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

        # Solo se reinicializan los datos de la SQLite
        # ficticia del simulador.
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
# CARGA DEL CATÁLOGO Y FACTURAS
# ============================================================

def _cargar_datos_iniciales(
    conexion: sqlite3.Connection,
) -> None:
    """
    Inserta conceptos y facturas ficticias.

    Los códigos MOCK-* no son códigos institucionales
    oficiales; representan los conceptos actualmente
    configurados en el simulador.
    """

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
        CONCEPTOS,
    )

    facturas = _generar_facturas_iniciales()

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
# CONSULTA DE FACTURAS
# ============================================================

def buscar_factura(
    numero_factura: str,
) -> dict[str, Any] | None:
    """
    Busca una factura por número.

    La validación de CI y código del concepto se realiza
    en main.py, conservando el comportamiento existente.
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

    return dict(fila)


def buscar_concepto(
    codigo: str,
) -> dict[str, Any] | None:
    """
    Consulta un concepto económico por su código.
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

    return dict(fila)
