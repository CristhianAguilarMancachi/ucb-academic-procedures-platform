import unittest

from app.services.rag import ingest


class EncabezadosNormativosTests(unittest.TestCase):

    def test_encabezados_validos(self):
        samples = [
            "ARTÍCULO 14°. (RENOVACIÓN DE LA BECA). -",
            "ARTICULO 8: Requisitos generales",
            "ARTÍCULO 1o. (OBJETO). -",
            "Artículo 3. Disposiciones generales",
            "ARTICULO 15°",
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                self.assertIsNotNone(
                    ingest.ARTICLE_HEADING_PATTERN.match(sample)
                )

    def test_referencias_no_son_encabezados(self):
        samples = [
            "Articulo 10° precedente y lo especificado",
            "Artículo 23 del presente Reglamento",
            "ARTÍCULO 8 conforme a la norma",
            "Según el Artículo 14°",
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                self.assertIsNone(
                    ingest.ARTICLE_HEADING_PATTERN.match(sample)
                )

    def test_referencia_permanece_en_articulo_original(self):
        pages = [{
            "page_number": 8,
            "text": (
                "ARTÍCULO 13°. (REVOCATORIA). -\n"
                "Las sanciones disciplinarias son causal de revocatoria.\n"
                "ARTÍCULO 14°. (RENOVACIÓN DE LA BECA). -\n"
                "Para renovar debe cumplirse lo dispuesto en el\n"
                "Articulo 10° precedente y los requisitos específicos."
            ),
        }]

        blocks = ingest.split_normative_blocks(pages)

        self.assertEqual(len(blocks), 2)

        self.assertIn(
            "ARTÍCULO 14°",
            blocks[1]["articulo_numero"]
        )

        self.assertIn(
            "Articulo 10° precedente",
            blocks[1]["content"]
        )

    def test_encabezados_sin_regresion(self):
        pages = [{
            "page_number": 1,
            "text": (
                "ARTICULO 1. Primera norma.\n"
                "Texto del primer artículo.\n"
                "ARTICULO 2. Segunda norma.\n"
                "Texto del segundo artículo."
            ),
        }]

        blocks = ingest.split_normative_blocks(pages)

        self.assertEqual(len(blocks), 2)

        self.assertEqual(
            [block["articulo_numero"] for block in blocks],
            ["ARTICULO 1", "ARTICULO 2"],
        )


if __name__ == "__main__":
    unittest.main()
