from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any


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


def _crear_directorio() -> None:
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def obtener_conexion() -> sqlite3.Connection:
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


def inicializar_base_datos() -> None:
    """
    Crea una base independiente para simular un sistema
    institucional de facturación/pagos.

    Los códigos MOCK no pretenden representar códigos
    institucionales reales.
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

        _cargar_datos_iniciales(
            conexion
        )


def _cargar_datos_iniciales(
    conexion: sqlite3.Connection,
) -> None:
    """
    Datos exclusivamente destinados a pruebas.

    Se utilizan conceptos económicos cuyos montos ya
    conocemos, pero los códigos son ficticios.
    """
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
        INSERT OR IGNORE INTO concepto_pago (
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

    facturas = [
        # -------------------------------------------------
        # CASO CORRECTO: certificado 55 BOB
        # -------------------------------------------------
        (
            "FAC-2026-000001",
            "MOCK-CERT-CONCLUSION-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-08-10T09:00:00-04:00",
            "2026-08-10T09:05:00-04:00",
            0,
        ),

        # -------------------------------------------------
        # CASO CORRECTO: título 1300 BOB
        # -------------------------------------------------
        (
            "FAC-2026-000002",
            "MOCK-TITULO-001",
            "1300.00",
            "BOB",
            "pagada",
            "2026-08-11T10:00:00-04:00",
            "2026-08-11T10:03:00-04:00",
            0,
        ),

        # -------------------------------------------------
        # FACTURA ANULADA
        # -------------------------------------------------
        (
            "FAC-2026-000003",
            "MOCK-LEGALIZACION-001",
            "110.00",
            "BOB",
            "anulada",
            "2026-08-12T08:30:00-04:00",
            None,
            0,
        ),

        # -------------------------------------------------
        # FACTURA YA UTILIZADA EXTERNAMENTE
        # -------------------------------------------------
        (
            "FAC-2026-000004",
            "MOCK-CERT-CONCLUSION-001",
            "55.00",
            "BOB",
            "pagada",
            "2026-08-13T14:00:00-04:00",
            "2026-08-13T14:01:00-04:00",
            1,
        ),

        # -------------------------------------------------
        # MONTO INCORRECTO
        # -------------------------------------------------
        (
            "FAC-2026-000005",
            "MOCK-CERT-CONCLUSION-001",
            "50.00",
            "BOB",
            "pagada",
            "2026-08-14T11:00:00-04:00",
            "2026-08-14T11:02:00-04:00",
            0,
        ),

        # -------------------------------------------------
        # FACTURA TODAVÍA PENDIENTE
        # -------------------------------------------------
        (
            "FAC-2026-000006",
            "MOCK-CERT-NOTAS-001",
            "55.00",
            "BOB",
            "pendiente",
            "2026-08-15T12:00:00-04:00",
            None,
            0,
        ),

        # -------------------------------------------------
        # OTRO CONCEPTO PARA PROBAR CÓDIGO INCORRECTO
        # -------------------------------------------------
        (
            "FAC-2026-000007",
            "MOCK-SUPLETORIO-001",
            "880.00",
            "BOB",
            "pagada",
            "2026-08-16T09:20:00-04:00",
            "2026-08-16T09:22:00-04:00",
            0,
        ),
    ]

    conexion.executemany(
        """
        INSERT OR IGNORE INTO factura (
            numero_factura,
            codigo_concepto,
            monto_pagado,
            moneda,
            estado,
            fecha_emision,
            fecha_pago,
            utilizada
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        facturas,
    )


def buscar_factura(
    numero_factura: str,
) -> dict[str, Any] | None:
    """
    Busca una factura y devuelve también información
    del concepto económico al que pertenece.
    """
    with obtener_conexion() as conexion:
        fila = conexion.execute(
            """
            SELECT
                f.numero_factura,
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