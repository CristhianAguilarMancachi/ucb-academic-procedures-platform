"""Integración de Conclusión de Estudios en Certificados Académicos.

Uso:
    python scripts/integrar_certificado_conclusion.py
        Simula y revierte todos los cambios.

    python scripts/integrar_certificado_conclusion.py --apply
        Aplica la migración en una transacción.

No modifica solicitudes históricas ni sus snapshots.
"""

from __future__ import annotations

import argparse
import json
import os

from sqlalchemy import create_engine, text


TRAMITE_ORIGEN = 7
TRAMITE_DESTINO = 8
CAMPO_TIPO = 6

REQUISITO_PAGO_ORIGEN = 32
REQUISITO_FORMULARIO_ORIGEN = 33
REQUISITO_PAGO_GENERAL = 34
REQUISITO_FORMULARIO_GENERAL = 35

TIPO_CONCLUSION = "Certificado de Conclusión de Estudios"
RESTRICCION = "ck_tramite_requisito_condicion"


def ejecutar(conn, sql, **parametros):
    return conn.execute(text(sql), parametros)


def exigir(condicion, mensaje):
    if not condicion:
        raise RuntimeError(mensaje)


def condicion(operador):
    return json.dumps(
        {
            "origen": "solicitud_dato",
            "clave": "tipo_certificado",
            "operador": operador,
            "valor": TIPO_CONCLUSION,
        },
        ensure_ascii=False,
    )


def aplicar_migracion(conn):
    ejecutar(conn, "SET LOCAL statement_timeout = '30000ms'")

    print("========== 1. BLOQUEAR CONFIGURACIÓN ==========")

    tramites = ejecutar(
        conn,
        """
        SELECT id_tramite, nombre, activo,
               publicado, permite_solicitudes
        FROM tramite
        WHERE id_tramite IN (7, 8)
        ORDER BY id_tramite
        FOR UPDATE
        """,
    ).mappings().all()

    exigir(len(tramites) == 2, "Faltan los trámites 7 u 8.")

    por_id = {r["id_tramite"]: r for r in tramites}

    exigir(
        por_id[7]["nombre"] == TIPO_CONCLUSION,
        "El trámite 7 no coincide con el esperado.",
    )
    exigir(
        por_id[8]["nombre"] == "Certificados Académicos",
        "El trámite 8 no coincide con el esperado.",
    )
    exigir(
        por_id[8]["activo"]
        and por_id[8]["publicado"]
        and por_id[8]["permite_solicitudes"],
        "El trámite 8 debe encontrarse habilitado.",
    )

    print("Trámites identificados correctamente.")

    print("========== 2. VERIFICAR CONFIGURACIÓN ACTUAL ==========")

    campo = ejecutar(
        conn,
        """
        SELECT id_campo, clave, tipo_dato,
               obligatorio, activo, configuracion
        FROM tramite_campo
        WHERE id_campo = :id
          AND id_tramite = :tramite
        FOR UPDATE
        """,
        id=CAMPO_TIPO,
        tramite=TRAMITE_DESTINO,
    ).mappings().one_or_none()

    exigir(campo is not None, "No existe el campo tipo_certificado.")
    exigir(
        campo["clave"] == "tipo_certificado"
        and campo["tipo_dato"] == "seleccion"
        and campo["obligatorio"]
        and campo["activo"],
        "La configuración del campo de certificados cambió.",
    )

    opciones = campo["configuracion"].get("opciones", [])

    exigir(
        isinstance(opciones, list)
        and all(isinstance(opcion, str) for opcion in opciones),
        "Las opciones actuales no tienen el formato esperado.",
    )

    requisitos = ejecutar(
        conn,
        """
        SELECT id_requisito, id_tramite, nombre,
               descripcion, obligatorio, orden, activo,
               requiere_presentacion_fisica, condicion
        FROM tramite_requisito
        WHERE id_requisito IN (32, 33, 34, 35)
        ORDER BY id_requisito
        FOR UPDATE
        """,
    ).mappings().all()

    exigir(len(requisitos) == 4, "Faltan requisitos originales.")

    por_requisito = {r["id_requisito"]: r for r in requisitos}

    for identificador in (32, 33):
        exigir(
            por_requisito[identificador]["id_tramite"] == 7,
            f"El requisito {identificador} no pertenece al trámite 7.",
        )

    for identificador in (34, 35):
        exigir(
            por_requisito[identificador]["id_tramite"] == 8,
            f"El requisito {identificador} no pertenece al trámite 8.",
        )

    exigir(
        por_requisito[33]["requiere_presentacion_fisica"],
        "No se identificó el requisito de dos ejemplares.",
    )
    exigir(
        por_requisito[35]["requiere_presentacion_fisica"],
        "No se identificó el formulario general.",
    )

    for id_requisito in (34, 35):
        actual = por_requisito[id_requisito]["condicion"]
        esperado = json.loads(condicion("distinto"))

        exigir(
            actual is None or actual == esperado,
            f"El requisito {id_requisito} tiene una condición inesperada.",
        )

    economicos = ejecutar(
        conn,
        """
        SELECT id_requisito, concepto, monto, moneda,
               gestion, codigo_concepto_externo, activo
        FROM tramite_requisito_economico
        WHERE id_requisito IN (32, 34)
        ORDER BY id_requisito, gestion
        """,
    ).mappings().all()

    origen = [r for r in economicos if r["id_requisito"] == 32]
    general = [r for r in economicos if r["id_requisito"] == 34]

    exigir(origen and general, "Falta una configuración económica.")

    for registro in origen + general:
        exigir(
            registro["monto"] == 55
            and registro["moneda"] == "BOB"
            and registro["codigo_concepto_externo"],
            "Se encontró una configuración económica incompatible.",
        )

    exigir(
        {r["gestion"] for r in origen}
        == {r["gestion"] for r in general},
        "Las gestiones económicas de los certificados no coinciden.",
    )

    print("Requisitos y pagos originales: correctos.")
    print("Gestiones:", sorted(r["gestion"] for r in origen))

    print("========== 3. ACTUALIZAR OPERADORES EN POSTGRESQL ==========")

    restriccion = ejecutar(
        conn,
        """
        SELECT pg_get_constraintdef(oid) AS definicion
        FROM pg_constraint
        WHERE conrelid = 'tramite_requisito'::regclass
          AND conname = :nombre
        """,
        nombre=RESTRICCION,
    ).scalar_one_or_none()

    exigir(
        restriccion is not None,
        "No se encontró la restricción de condiciones.",
    )

    print("Restricción actual:", restriccion)

    exigir(
        "operador" in restriccion
        and ("igual" in restriccion),
        "La restricción actual no coincide con la esperada.",
    )

    if "distinto" not in restriccion:
        ejecutar(
            conn,
            """
            ALTER TABLE tramite_requisito
            DROP CONSTRAINT ck_tramite_requisito_condicion
            """,
        )

        ejecutar(
            conn,
            """
            ALTER TABLE tramite_requisito
            ADD CONSTRAINT ck_tramite_requisito_condicion
            CHECK (
                condicion IS NULL
                OR (
                    jsonb_typeof(condicion) = 'object'
                    AND condicion->>'operador'
                        IN ('igual', 'distinto')
                    AND condicion->>'origen'
                        IN ('solicitud_dato', 'perfil_academico')
                )
            )
            """,
        )

        print("Restricción ampliada a igual/distinto.")
    else:
        print("La restricción ya admite distinto.")

    print("========== 4. AGREGAR DÉCIMO CERTIFICADO ==========")

    if TIPO_CONCLUSION not in opciones:
        configuracion = dict(campo["configuracion"])
        configuracion["opciones"] = [
            *opciones,
            TIPO_CONCLUSION,
        ]

        ejecutar(
            conn,
            """
            UPDATE tramite_campo
            SET configuracion = CAST(:configuracion AS jsonb),
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id_campo = :id
            """,
            configuracion=json.dumps(
                configuracion,
                ensure_ascii=False,
            ),
            id=CAMPO_TIPO,
        )

        print("Agregada la décima opción.")
    else:
        print("La opción ya está presente.")

    print("========== 5. CONDICIONAR REQUISITOS GENERALES ==========")

    regla_distinto = condicion("distinto")
    regla_igual = condicion("igual")

    ejecutar(
        conn,
        """
        UPDATE tramite_requisito
        SET condicion = CAST(:regla AS jsonb),
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_requisito IN (34, 35)
        """,
        regla=regla_distinto,
    )

    print("Pago y formulario generales: solo para otros certificados.")

    print("========== 6. INCORPORAR REQUISITOS ESPECÍFICOS ==========")

    nuevos_ids = {}

    for origen_id, tipo in (
        (REQUISITO_PAGO_ORIGEN, "pago"),
        (REQUISITO_FORMULARIO_ORIGEN, "formulario"),
    ):
        original = por_requisito[origen_id]

        existentes = ejecutar(
            conn,
            """
            SELECT id_requisito
            FROM tramite_requisito
            WHERE id_tramite = 8
              AND nombre = :nombre
              AND condicion = CAST(:regla AS jsonb)
            """,
            nombre=original["nombre"],
            regla=regla_igual,
        ).scalars().all()

        exigir(
            len(existentes) <= 1,
            f"Hay requisitos duplicados para {tipo}.",
        )

        if existentes:
            nuevo_id = existentes[0]
            print(f"Requisito {tipo} ya existente: {nuevo_id}")
        else:
            nuevo_id = ejecutar(
                conn,
                """
                INSERT INTO tramite_requisito (
                    id_tramite,
                    nombre,
                    descripcion,
                    obligatorio,
                    orden,
                    activo,
                    requiere_presentacion_fisica,
                    condicion
                )
                VALUES (
                    8,
                    :nombre,
                    :descripcion,
                    :obligatorio,
                    :orden,
                    :activo,
                    :fisico,
                    CAST(:regla AS jsonb)
                )
                RETURNING id_requisito
                """,
                nombre=original["nombre"],
                descripcion=original["descripcion"],
                obligatorio=original["obligatorio"],
                orden=original["orden"],
                activo=original["activo"],
                fisico=original["requiere_presentacion_fisica"],
                regla=regla_igual,
            ).scalar_one()

            print(f"Requisito {tipo} creado: {nuevo_id}")

        nuevos_ids[tipo] = nuevo_id

    print("========== 7. COPIAR CONFIGURACIONES ECONÓMICAS ==========")

    nuevo_pago = nuevos_ids["pago"]

    for config in origen:
        existente = ejecutar(
            conn,
            """
            SELECT id_requisito_economico,
                   concepto, monto, moneda,
                   codigo_concepto_externo, activo
            FROM tramite_requisito_economico
            WHERE id_requisito = :id
              AND gestion = :gestion
            """,
            id=nuevo_pago,
            gestion=config["gestion"],
        ).mappings().one_or_none()

        if existente:
            exigir(
                existente["concepto"] == config["concepto"]
                and existente["monto"] == config["monto"]
                and existente["moneda"] == config["moneda"]
                and existente["codigo_concepto_externo"]
                    == config["codigo_concepto_externo"]
                and existente["activo"] == config["activo"],
                "Existe una configuración económica específica diferente.",
            )
            print(f"Gestión {config['gestion']}: ya configurada.")
            continue

        ejecutar(
            conn,
            """
            INSERT INTO tramite_requisito_economico (
                id_requisito,
                concepto,
                monto,
                moneda,
                gestion,
                codigo_concepto_externo,
                activo
            )
            VALUES (
                :id,
                :concepto,
                :monto,
                :moneda,
                :gestion,
                :codigo,
                :activo
            )
            """,
            id=nuevo_pago,
            concepto=config["concepto"],
            monto=config["monto"],
            moneda=config["moneda"],
            gestion=config["gestion"],
            codigo=config["codigo_concepto_externo"],
            activo=config["activo"],
        )

        print(f"Gestión {config['gestion']}: concepto incorporado.")

    print("========== 8. ACTUALIZAR CATÁLOGO ==========")

    ejecutar(
        conn,
        """
        UPDATE tramite
        SET publicado = FALSE,
            permite_solicitudes = FALSE,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_tramite = 7
        """,
    )

    descripcion = (
        " Incluye Certificado de Conclusión de Estudios."
    )

    instrucciones = (
        " Para Certificado de Conclusión de Estudios "
        "se requieren dos ejemplares del Formulario "
        "de Solicitud: uno para Kardex y otro para "
        "la carrera del estudiante."
    )

    ejecutar(
        conn,
        """
        UPDATE tramite
        SET descripcion = CASE
                WHEN descripcion ILIKE :patron
                    THEN descripcion
                ELSE COALESCE(descripcion, '') || :descripcion
            END,
            instrucciones = CASE
                WHEN instrucciones ILIKE :patron
                    THEN instrucciones
                ELSE COALESCE(instrucciones, '') || :instrucciones
            END,
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_tramite = 8
        """,
        patron="%Certificado de Conclusión de Estudios%",
        descripcion=descripcion,
        instrucciones=instrucciones,
    )

    print("Trámite 7 despublicado.")
    print("Trámite 8 actualizado.")

    print("========== 9. VALIDACIONES POSTERIORES ==========")

    opciones_finales = ejecutar(
        conn,
        """
        SELECT configuracion->'opciones'
        FROM tramite_campo
        WHERE id_campo = 6
        """,
    ).scalar_one()

    exigir(
        opciones_finales.count(TIPO_CONCLUSION) == 1,
        "El tipo de conclusión no aparece exactamente una vez.",
    )

    verificar = ejecutar(
        conn,
        """
        SELECT nombre, condicion,
               requiere_presentacion_fisica
        FROM tramite_requisito
        WHERE id_tramite = 8
          AND activo = TRUE
        """,
    ).mappings().all()

    exigir(
        len(verificar) == 4,
        "El trámite 8 debe tener cuatro requisitos activos.",
    )

    for tipo in opciones_finales:
        aplicables = [
            r for r in verificar
            if r["condicion"] is None
            or (
                (r["condicion"]["operador"] == "igual")
                == (tipo == TIPO_CONCLUSION)
            )
        ]

        exigir(
            len(aplicables) == 2,
            f"El certificado {tipo!r} no tiene exactamente dos requisitos.",
        )

        exigir(
            sum(bool(r["requiere_presentacion_fisica"]) for r in aplicables)
            == 1,
            f"Formulario incorrecto para {tipo}.",
        )

        ids = ejecutar(
            conn,
            """
            SELECT COUNT(*)
            FROM tramite_requisito_economico e
            JOIN tramite_requisito r
              ON r.id_requisito = e.id_requisito
            WHERE r.id_tramite = 8
              AND r.nombre = :nombre
              AND r.condicion = CAST(:condicion AS jsonb)
            """,
            nombre=(
                por_requisito[32]["nombre"]
                if tipo == TIPO_CONCLUSION
                else por_requisito[34]["nombre"]
            ),
            condicion=(
                regla_igual
                if tipo == TIPO_CONCLUSION
                else regla_distinto
            ),
        ).scalar_one()

        exigir(
            ids == len(origen if tipo == TIPO_CONCLUSION else general),
            f"Concepto económico incorrecto para {tipo}.",
        )

    historicas = ejecutar(
        conn,
        """
        SELECT id_tramite, COUNT(*)
        FROM solicitud
        WHERE id_tramite IN (7, 8)
        GROUP BY id_tramite
        ORDER BY id_tramite
        """,
    ).all()

    print("Solicitudes históricas:", historicas)
    print("Opciones:", len(opciones_finales))
    print("Requisitos activos del trámite 8:", len(verificar))
    print("Validaciones: correctas.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplicar y confirmar la transacción.",
    )
    args = parser.parse_args()

    engine = create_engine(
        os.environ["DATABASE_URL"],
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as conn:
            transaccion = conn.begin()

            try:
                aplicar_migracion(conn)

                if args.apply:
                    transaccion.commit()
                    print()
                    print("MIGRACIÓN APLICADA CORRECTAMENTE.")
                else:
                    transaccion.rollback()
                    print()
                    print("SIMULACIÓN CORRECTA.")
                    print("ROLLBACK EJECUTADO: SIN CAMBIOS PERSISTENTES.")

            except Exception:
                if transaccion.is_active:
                    transaccion.rollback()
                raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
