import unittest
from types import SimpleNamespace

from app.services.rag.retriever import (
    select_with_query_coverage,
)


def candidate(identifier, distance, score):
    return {
        "chunk": SimpleNamespace(
            id_chunk_documento=identifier
        ),
        "distance": distance,
        "semantic_score": 1.0 - distance,
        "lexical_score": 0.0,
        "combined_score": score,
        "fusion_score": score,
    }


def ids(items):
    return [
        item["chunk"].id_chunk_documento
        for item in items
    ]


class CoberturaSemanticaTests(unittest.TestCase):

    def test_conserva_evidencia_de_dos_subpreguntas(self):
        first = [
            candidate(8, 0.3216, 0.6410),
            candidate(10, 0.2856, 0.6394),
            candidate(15, 0.3474, 0.6242),
            candidate(9, 0.3171, 0.5689),
            candidate(35, 0.3110, 0.5479),
            candidate(13, 0.2221, 0.5306),
        ]

        second = [
            candidate(10, 0.5040, 0.3974),
            candidate(14, 0.4250, 0.3737),
            candidate(16, 0.5378, 0.3254),
        ]

        fused = [
            candidate(10, 0.2022, 0.7845),
            candidate(35, 0.2799, 0.6854),
            candidate(16, 0.2803, 0.6615),
            candidate(8, 0.3216, 0.6525),
            candidate(14, 0.2133, 0.5730),
            candidate(13, 0.2405, 0.5624),
        ]

        result = select_with_query_coverage(
            fused_results=fused,
            primary_ranked_results=[first, second],
            effective_top_k=4,
        )

        self.assertEqual(len(result), 4)
        self.assertIn(13, ids(result))
        self.assertIn(14, ids(result))

    def test_reserva_no_desaparece_en_el_corte(self):
        first = [
            candidate(101, 0.10, 0.75),
        ]

        second = [
            candidate(202, 0.12, 0.74),
        ]

        fused = [
            candidate(1, 0.20, 0.99),
            candidate(2, 0.22, 0.98),
            candidate(3, 0.24, 0.97),
            candidate(101, 0.10, 0.80),
            candidate(202, 0.12, 0.79),
        ]

        result = select_with_query_coverage(
            fused,
            [first, second],
            3,
        )

        self.assertEqual(len(result), 3)
        self.assertIn(101, ids(result))
        self.assertIn(202, ids(result))

    def test_conserva_hibrido_sin_ventaja_clara(self):
        ranked = [
            candidate(1, 0.30, 0.85),
            candidate(2, 0.27, 0.79),
        ]

        fused = [
            candidate(1, 0.30, 0.85),
            candidate(2, 0.27, 0.79),
        ]

        result = select_with_query_coverage(
            fused,
            [ranked],
            1,
        )

        self.assertEqual(ids(result), [1])

    def test_no_fuerza_coincidencia_semantica_debil(self):
        ranked = [
            candidate(1, 0.61, 0.80),
            candidate(2, 0.52, 0.65),
        ]

        result = select_with_query_coverage(
            ranked,
            [ranked],
            1,
        )

        self.assertEqual(ids(result), [1])

    def test_consulta_sin_subpreguntas(self):
        fused = [
            candidate(1, 0.20, 0.90),
            candidate(2, 0.25, 0.80),
        ]

        result = select_with_query_coverage(
            fused,
            [],
            1,
        )

        self.assertEqual(ids(result), [1])

    def test_no_duplica_fragmentos(self):
        ranked = [
            candidate(1, 0.20, 0.90),
            candidate(2, 0.25, 0.80),
        ]

        result = select_with_query_coverage(
            ranked,
            [ranked, ranked],
            2,
        )

        self.assertEqual(ids(result), [1, 2])


if __name__ == "__main__":
    unittest.main()
