
import json
import unittest
from unittest.mock import patch

from app.services.rag.claim_grounding_service import (
    build_claim_audit_prompt,
    evidence_exists,
    find_supporting_document,
    parse_audit_json,
    render_supported_claims,
    validate_claims_grounded_answer,
)
from app.services.rag.prompt_builder import (
    NO_INFORMATION_MESSAGE,
)


class ClaimGroundingServiceTests(unittest.TestCase):

    def setUp(self):
        self.documents = [
            (
                "Los servicios A, B y C tienen "
                "el mismo costo. "
                "El servicio D incluye los componentes E y F. "
                "Para recoger el documento A se requiere "
                "una carta de autorización. "
                "Para recoger el documento B se requiere "
                "un poder notarial original."
            )
        ]

    def make_claim(
        self,
        text,
        claim_type="fact",
        supported=True,
        evidence="",
        scope_evidence="",
        relation_evidence="",
    ):
        return {
            "text": text,
            "supported": supported,
            "claim_type": claim_type,
            "evidence": evidence,
            "scope_evidence": scope_evidence,
            "relation_evidence": relation_evidence,
        }

    def test_evidencia_existente(self):
        self.assertTrue(
            evidence_exists(
                "Los servicios A, B y C tienen el mismo costo.",
                self.documents,
            )
        )

    def test_evidencia_inexistente(self):
        self.assertFalse(
            evidence_exists(
                "El servicio A incluye B y C.",
                self.documents,
            )
        )

    def test_prompt_comprueba_alcance_y_relaciones(self):
        prompt = build_claim_audit_prompt(
            question="¿Qué contiene A?",
            answer="A incluye B y C.",
            documents=self.documents,
        )

        self.assertIn("ALCANCE DOCUMENTAL", prompt)
        self.assertIn("RELACIÓN DOCUMENTAL", prompt)
        self.assertIn("scope_evidence", prompt)
        self.assertIn("relation_evidence", prompt)

    def test_json_invalido(self):
        self.assertIsNone(
            parse_audit_json("respuesta en texto libre")
        )

    def test_json_con_campos_incompletos(self):
        self.assertIsNone(
            parse_audit_json(
                json.dumps({
                    "claims": [
                        {
                            "text": "A incluye B.",
                            "supported": True,
                            "evidence": "A y B",
                        }
                    ]
                })
            )
        )

    def test_rechaza_inclusion_sin_relacion(self):
        claim = self.make_claim(
            text="El servicio A incluye B y C.",
            claim_type="inclusion",
            evidence=(
                "Los servicios A, B y C tienen el mismo costo."
            ),
            scope_evidence=(
                "Los servicios A, B y C tienen el mismo costo."
            ),
            relation_evidence="",
        )

        self.assertIsNone(
            find_supporting_document(
                claim,
                self.documents,
            )
        )

    def test_no_permite_disfrazar_inclusion_como_hecho(self):
        claim = self.make_claim(
            text="El servicio A incluye B y C.",
            claim_type="fact",
            evidence=(
                "Los servicios A, B y C tienen el mismo costo."
            ),
            scope_evidence=(
                "Los servicios A, B y C tienen el mismo costo."
            ),
        )

        self.assertIsNone(
            find_supporting_document(
                claim,
                self.documents,
            )
        )

    def test_conserva_inclusion_documentada(self):
        evidence = (
            "El servicio D incluye los componentes E y F."
        )

        claim = self.make_claim(
            text="El servicio D incluye E y F.",
            claim_type="inclusion",
            evidence=evidence,
            scope_evidence=evidence,
            relation_evidence=evidence,
        )

        self.assertEqual(
            render_supported_claims(
                [claim],
                self.documents,
            ),
            "El servicio D incluye E y F.",
        )

    def test_rechaza_requisito_sin_alcance(self):
        claim = self.make_claim(
            text=(
                "Para recoger el documento A se requiere "
                "un poder notarial."
            ),
            claim_type="requirement",
            evidence=(
                "Para recoger el documento B se requiere "
                "un poder notarial original."
            ),
            scope_evidence=(
                "Para recoger el documento A se requiere "
                "un poder notarial."
            ),
            relation_evidence=(
                "Para recoger el documento B se requiere "
                "un poder notarial original."
            ),
        )

        self.assertIsNone(
            find_supporting_document(
                claim,
                self.documents,
            )
        )

    def test_conserva_requisito_correcto(self):
        evidence = (
            "Para recoger el documento A se requiere "
            "una carta de autorización."
        )

        claim = self.make_claim(
            text=(
                "Para recoger el documento A se requiere "
                "una carta de autorización."
            ),
            claim_type="requirement",
            evidence=evidence,
            scope_evidence=evidence,
            relation_evidence=evidence,
        )

        self.assertEqual(
            render_supported_claims(
                [claim],
                self.documents,
            ),
            claim["text"],
        )

    def test_conserva_respuesta_parcial(self):
        evidence = (
            "Para recoger el documento A se requiere "
            "una carta de autorización."
        )

        valid = self.make_claim(
            text=evidence,
            claim_type="requirement",
            evidence=evidence,
            scope_evidence=evidence,
            relation_evidence=evidence,
        )

        invalid = self.make_claim(
            text=(
                "Para recoger el documento A se requiere "
                "un poder notarial."
            ),
            claim_type="requirement",
            supported=False,
        )

        result = render_supported_claims(
            [valid, invalid],
            self.documents,
        )

        self.assertIn("carta de autorización", result)
        self.assertNotIn("poder notarial", result)

    @patch(
        "app.services.rag.claim_grounding_service.complete_text"
    )
    def test_auditoria_realiza_una_llamada(self, mock_llm):
        evidence = (
            "Para recoger el documento A se requiere "
            "una carta de autorización."
        )

        mock_llm.return_value = json.dumps({
            "claims": [
                self.make_claim(
                    text=evidence,
                    claim_type="requirement",
                    evidence=evidence,
                    scope_evidence=evidence,
                    relation_evidence=evidence,
                )
            ]
        })

        result = validate_claims_grounded_answer(
            question="¿Qué se requiere para recoger A?",
            answer=evidence,
            documents=self.documents,
        )

        self.assertIn("carta de autorización", result)
        mock_llm.assert_called_once()

    @patch(
        "app.services.rag.claim_grounding_service.complete_text"
    )
    def test_formato_invalido_no_publica_respuesta(
        self,
        mock_llm,
    ):
        mock_llm.return_value = "texto no estructurado"

        result = validate_claims_grounded_answer(
            question="¿Qué incluye A?",
            answer="A incluye B y C.",
            documents=self.documents,
        )

        self.assertEqual(
            result,
            NO_INFORMATION_MESSAGE,
        )
        mock_llm.assert_called_once()

    @patch(
        "app.services.rag.claim_grounding_service.complete_text"
    )
    def test_sin_afirmaciones_validas_no_inventa(
        self,
        mock_llm,
    ):
        mock_llm.return_value = json.dumps({
            "claims": [
                self.make_claim(
                    text="A incluye B y C.",
                    claim_type="inclusion",
                    supported=False,
                )
            ]
        })

        result = validate_claims_grounded_answer(
            question="¿Qué incluye A?",
            answer="A incluye B y C.",
            documents=self.documents,
        )

        self.assertEqual(
            result,
            NO_INFORMATION_MESSAGE,
        )


if __name__ == "__main__":
    unittest.main()
