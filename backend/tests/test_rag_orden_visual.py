import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app.services.rag import ingest


class OrdenVisualNormativoTests(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "norma.pdf"

    def create_scrambled_pdf(self):
        with fitz.open() as pdf:
            page = pdf.new_page()

            page.insert_text(
                (50, 180),
                "ARTICULO 3. Requisito tercero",
            )
            page.insert_text(
                (50, 60),
                "ARTICULO 1. Requisito primero",
            )
            page.insert_text(
                (50, 120),
                "ARTICULO 2. Requisito segundo",
            )

            pdf.save(self.path)

    def test_orden_visual_corrige_articulos_invertidos(self):
        self.create_scrambled_pdf()

        pages = ingest.extract_text_by_page_hybrid(self.path)
        corrected = ingest.prefer_sorted_normative_text(
            self.path, pages
        )

        text = corrected[0]["text"]

        self.assertLess(
            text.index("ARTICULO 1"),
            text.index("ARTICULO 2"),
        )
        self.assertLess(
            text.index("ARTICULO 2"),
            text.index("ARTICULO 3"),
        )
        self.assertEqual(corrected[0]["page_number"], 1)

    def test_no_modifica_documento_ya_ordenado(self):
        self.create_scrambled_pdf()

        with fitz.open(self.path) as pdf:
            ordered = [{
                "page_number": 1,
                "text": pdf[0].get_text(
                    "text", sort=True
                ).strip(),
            }]

        result = ingest.prefer_sorted_normative_text(
            self.path, ordered
        )

        self.assertEqual(result, ordered)

    def test_no_modifica_pagina_ocr(self):
        self.create_scrambled_pdf()

        pages = [{
            "page_number": 1,
            "text": "Resultado recuperado por OCR",
        }]

        self.assertEqual(
            ingest.prefer_sorted_normative_text(
                self.path, pages
            ),
            pages,
        )

    def test_conserva_extraccion_con_articulos_distintos(self):
        self.create_scrambled_pdf()

        pages = ingest.extract_text_by_page_hybrid(self.path)
        pages[0]["text"] += (
            "\nARTICULO 99. Anexo adicional"
        )

        self.assertEqual(
            ingest.prefer_sorted_normative_text(
                self.path, pages
            ),
            pages,
        )

    def test_preparar_chunks_usa_orden_visual(self):
        self.create_scrambled_pdf()

        with patch.object(
            ingest,
            "create_embeddings",
            side_effect=lambda values: [
                [0.1] * 512 for _ in values
            ],
        ):
            _, chunks = ingest.preparar_chunks(self.path)

        articles = [
            chunk["articulo_numero"]
            for chunk in chunks
            if chunk["articulo_numero"]
        ]

        self.assertEqual(
            articles,
            [
                "ARTICULO 1",
                "ARTICULO 2",
                "ARTICULO 3",
            ],
        )


if __name__ == "__main__":
    unittest.main()
