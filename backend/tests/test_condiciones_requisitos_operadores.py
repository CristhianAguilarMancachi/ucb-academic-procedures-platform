import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import TypeAdapter, ValidationError

from app.schemas.gestion_seguimiento.seguimiento import (
    CondicionRequisito,
)
from app.services.gestion_seguimiento.configuracion_flujo_service import (
    igualdad_simple,
    requisitos_aplicables_sin_solicitud,
)


class CondicionesRequisitosOperadoresTests(unittest.TestCase):
    def test_operadores_admitidos(self):
        adaptador = TypeAdapter(CondicionRequisito)

        for operador in ("igual", "distinto"):
            regla = adaptador.validate_python({
                "origen": "solicitud_dato",
                "clave": "tipo_certificado",
                "operador": operador,
                "valor": "Certificado de Conclusión de Estudios",
            })

            self.assertEqual(regla.operador, operador)

        with self.assertRaises(ValidationError):
            adaptador.validate_python({
                "origen": "solicitud_dato",
                "clave": "tipo_certificado",
                "operador": "contiene",
                "valor": "Certificado",
            })

    def test_igualdad_distingue_booleanos(self):
        self.assertFalse(igualdad_simple(False, 0))
        self.assertFalse(igualdad_simple(True, 1))
        self.assertTrue(igualdad_simple("texto", "texto"))

    def test_requisitos_condicionales_no_se_duplican(self):
        tipo_conclusion = "Certificado de Conclusión de Estudios"

        campo = SimpleNamespace(
            id_campo=6,
            clave="tipo_certificado",
            activo=True,
        )

        general = SimpleNamespace(
            nombre="Formulario habitual",
            condicion={
                "origen": "solicitud_dato",
                "clave": "tipo_certificado",
                "operador": "distinto",
                "valor": tipo_conclusion,
            },
        )

        especifico = SimpleNamespace(
            nombre="Dos ejemplares",
            condicion={
                "origen": "solicitud_dato",
                "clave": "tipo_certificado",
                "operador": "igual",
                "valor": tipo_conclusion,
            },
        )

        requisitos = [general, especifico]

        with patch(
            "app.services.gestion_seguimiento."
            "configuracion_flujo_service.validar_condicion",
            side_effect=lambda condicion, _: (
                SimpleNamespace(**condicion) if condicion else None
            ),
        ), patch(
            "app.services.gestion_seguimiento."
            "configuracion_flujo_service."
            "seguimiento_repository.obtener_perfil",
            return_value=None,
        ):
            for seleccionado, esperado in (
                ("Certificado de Calificaciones", general),
                (tipo_conclusion, especifico),
            ):
                aplicables = requisitos_aplicables_sin_solicitud(
                    db=None,
                    id_solicitante=1,
                    requisitos=requisitos,
                    campos=[campo],
                    datos=[
                        SimpleNamespace(
                            id_campo=6,
                            valor=seleccionado,
                        )
                    ],
                )

                self.assertEqual(aplicables, [esperado])


if __name__ == "__main__":
    unittest.main()
