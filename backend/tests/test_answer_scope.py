
import unittest
from unittest.mock import patch

from app.services.rag.answer_scope import (
    keep_documented_relationships,
    scope_retrieved_context,
)
from app.services.rag.generator import (
    generate_answer,
)


class AnswerScopeTests(unittest.TestCase):

    def setUp(self):
        self.documents = [
            (
                "Certificado Supletorio. "
                "Paso 3: El documento se recoge en Registros. "
                "Las terceras personas presentan un poder "
                "notarial original o una copia legalizada."
            ),
            (
                "Certificado de Calificaciones, Alumno "
                "Regular, Carga Horaria, Promedios y Ranking. "
                "Paso 1: Llenar el formulario de solicitud. "
                "Paso 2: Realizar el pago de Bs. 55 en Caja."
            ),
            (
                "Paso 3: Entregar el formulario en Registro "
                "Académico. Paso 4: Para recoger el "
                "certificado, el interesado presenta su "
                "documento de identidad. Las terceras "
                "personas presentan carta de autorización."
            ),
        ]

        self.metadatas = [
            {
                "document": "Consultas institucionales",
                "page": 5,
            },
            {
                "document": "Consultas institucionales",
                "page": 7,
            },
            {
                "document": "Consultas institucionales",
                "page": 7,
            },
        ]

    def test_conserva_fragmentos_del_mismo_tema(self):
        documents, metadatas = (
            scope_retrieved_context(
                question=(
                    "Si alguien recoge mi certificado "
                    "de calificaciones, ¿qué presenta?"
                ),
                documents=self.documents,
                metadatas=self.metadatas,
            )
        )

        self.assertEqual(
            [meta["page"] for meta in metadatas],
            [7, 7],
        )

        combined = " ".join(documents)

        self.assertIn(
            "carta de autorización",
            combined,
        )

        self.assertNotIn(
            "poder notarial",
            combined,
        )

    def test_enumeraciones_utilizan_tema_correcto(self):
        documents, metadatas = (
            scope_retrieved_context(
                question=(
                    "¿El certificado de calificaciones "
                    "incluye ranking y carga horaria?"
                ),
                documents=self.documents,
                metadatas=self.metadatas,
            )
        )

        self.assertEqual(
            [meta["page"] for meta in metadatas],
            [7, 7],
        )

    def test_sin_tema_claro_conserva_contexto(self):
        documents, metadatas = (
            scope_retrieved_context(
                question="Tengo una consulta general.",
                documents=self.documents,
                metadatas=self.metadatas,
            )
        )

        self.assertEqual(
            documents,
            self.documents,
        )

        self.assertEqual(
            metadatas,
            self.metadatas,
        )

    def test_metadata_incompleta_no_descarta(self):
        documents, _ = scope_retrieved_context(
            question="Certificado de calificaciones",
            documents=self.documents,
            metadatas=self.metadatas[:1],
        )

        self.assertEqual(
            documents,
            self.documents,
        )

    def test_comparaciones_conservan_contexto(self):
        documents, _ = scope_retrieved_context(
            question=(
                "¿Qué diferencia existe entre "
                "el procedimiento A y B?"
            ),
            documents=self.documents,
            metadatas=self.metadatas,
        )

        self.assertEqual(
            documents,
            self.documents,
        )

    def test_rechaza_inclusion_no_documentada(self):
        result = keep_documented_relationships(
            question="¿El programa A incluye B y C?",
            answer=(
                "El programa A incluye los "
                "componentes B y C."
            ),
            documents=[
                "Programas A, B y C tienen "
                "una tarifa compartida."
            ],
        )

        self.assertIn(
            "no confirma",
            result,
        )

        self.assertNotIn(
            "A incluye",
            result,
        )

    def test_conserva_inclusion_explicita(self):
        source = (
            "El programa académico incluye "
            "prácticas y simulaciones."
        )

        result = keep_documented_relationships(
            question=(
                "¿Qué incluye el programa académico?"
            ),
            answer=source,
            documents=[source],
        )

        self.assertEqual(
            result,
            source,
        )

    def test_no_confunde_lista_con_inclusion(self):
        result = keep_documented_relationships(
            question=(
                "¿Los servicios A, B y C "
                "están incluidos?"
            ),
            answer=(
                "No es necesario solicitar "
                "documentos diferentes para "
                "obtener todos esos servicios."
            ),
            documents=[
                "Servicios A, B y C: precio común."
            ],
        )

        self.assertIn(
            "no confirma",
            result,
        )

    def test_conserva_procedimiento_correcto(self):
        answer = (
            "1. Llenar el formulario.\n"
            "2. Pagar Bs. 55.\n"
            "3. Entregar el documento."
        )

        result = keep_documented_relationships(
            question="¿Cómo realizo el trámite?",
            answer=answer,
            documents=[
                "Llenar formulario, pagar "
                "Bs. 55 y entregar documento."
            ],
        )

        self.assertEqual(
            result,
            answer,
        )

    def test_elimina_catalogo_no_solicitado(self):
        answer = (
            "El costo es Bs. 55 por el servicio A "
            "(servicio B, servicio C, servicio D, "
            "servicio E, servicio F)."
        )

        result = keep_documented_relationships(
            question="¿Cuánto cuesta el servicio A?",
            answer=answer,
            documents=[
                "El servicio A cuesta Bs. 55."
            ],
        )

        self.assertEqual(
            result,
            "El costo es Bs. 55 por el servicio A.",
        )

    def test_conserva_respuesta_parcial(self):
        result = keep_documented_relationships(
            question="¿Cuánto cuesta el programa?",
            answer=(
                "El programa incluye diferentes "
                "beneficios.\n\n"
                "El costo es Bs. 55."
            ),
            documents=[
                "El costo del programa es Bs. 55."
            ],
        )

        self.assertIn(
            "El costo es Bs. 55.",
            result,
        )

    @patch(
        "app.services.rag.generator."
        "validate_grounded_answer"
    )
    @patch(
        "app.services.rag.generator.complete_text"
    )
    @patch(
        "app.services.rag.generator.build_rag_prompt"
    )
    def test_integracion_del_generador(
        self,
        mock_prompt,
        mock_llm,
        mock_validator,
    ):
        mock_prompt.return_value = "Prompt de prueba"
        mock_llm.return_value = "Respuesta respaldada."
        mock_validator.return_value = (
            "Respuesta respaldada."
        )

        result = generate_answer(
            question=(
                "¿Cómo solicito un certificado "
                "de calificaciones?"
            ),
            documents=self.documents,
            metadatas=self.metadatas,
            query_type="procedure",
        )

        self.assertEqual(
            result,
            "Respuesta respaldada.",
        )

        selected = (
            mock_prompt.call_args.kwargs[
                "documents"
            ]
        )

        self.assertEqual(
            len(selected),
            2,
        )

        self.assertEqual(
            mock_llm.call_count,
            1,
        )

        self.assertEqual(
            mock_validator.call_count,
            1,
        )


if __name__ == "__main__":
    unittest.main()
