import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz

from app.services.rag import ingest


class IngestaHibridaTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "prueba.pdf"

    def create_pdf(self, scanned=False):
        with fitz.open() as pdf:
            first = pdf.new_page()
            first.insert_text(
                (60, 80),
                "Documento digital para validar la extracción."
            )

            if scanned:
                with fitz.open() as original:
                    page = original.new_page()
                    page.insert_text(
                        (60, 80),
                        "ARTICULO 8: Cuatro asignaturas aprobadas.",
                        fontsize=18,
                    )
                    image = page.get_pixmap(
                        dpi=150
                    ).tobytes("png")

                second = pdf.new_page()
                second.insert_image(
                    second.rect,
                    stream=image,
                )

            pdf.save(self.file)

    def test_documento_digital_no_necesita_ocr(self):
        self.create_pdf()

        with patch.object(
            ingest,
            "recognize_page",
        ) as ocr:
            pages = ingest.extract_text_by_page_hybrid(
                self.file
            )

        self.assertEqual(len(pages), 1)
        self.assertIn("Documento digital", pages[0]["text"])
        ocr.assert_not_called()

    def test_documento_mixto_procesa_solo_escaneo(self):
        self.create_pdf(scanned=True)

        with (
            patch.object(
                ingest,
                "get_ocr_languages",
                return_value="spa+eng",
            ),
            patch.object(
                ingest,
                "recognize_page",
                return_value=(
                    "ARTICULO 8: Cuatro asignaturas aprobadas."
                ),
            ) as ocr,
        ):
            pages = ingest.extract_text_by_page_hybrid(
                self.file
            )

        self.assertEqual(len(pages), 2)
        self.assertEqual(ocr.call_count, 1)
        self.assertIn("ARTICULO 8", pages[1]["text"])

    def test_ocr_fallido_no_genera_embeddings(self):
        self.create_pdf(scanned=True)

        with (
            patch.object(
                ingest,
                "get_ocr_languages",
                return_value="spa+eng",
            ),
            patch.object(
                ingest,
                "recognize_page",
                side_effect=RuntimeError("OCR no disponible"),
            ),
            patch.object(
                ingest,
                "create_embeddings",
            ) as embedding,
        ):
            with self.assertRaises(RuntimeError):
                ingest.preparar_chunks(self.file)

            embedding.assert_not_called()

    def test_normativa_separa_circular(self):
        pages = [
            {
                "page_number": 1,
                "text": "Portada institucional",
            },
            {
                "page_number": 2,
                "text": (
                    "ARTÍCULO 8. Requisitos.\n"
                    "Cuatro asignaturas aprobadas."
                ),
            },
            {
                "page_number": 3,
                "text": (
                    "Vicerrectorado Académico\n"
                    "CIRCULAR VAN 02/2024\n"
                    "No cobro."
                ),
            },
        ]

        chunks = ingest.split_normative_with_attachments(
            pages
        )

        normative = [
            c for c in chunks
            if c.get("articulo_numero")
        ]

        attachments = [
            c for c in chunks
            if c["pagina_inicio"] == 3
        ]

        self.assertTrue(normative)
        self.assertTrue(attachments)

        self.assertFalse(
            any(
                "CIRCULAR" in c["content"]
                for c in normative
            )
        )

    def test_embeddings_conservan_pagina(self):
        self.create_pdf(scanned=True)

        with (
            patch.object(
                ingest,
                "get_ocr_languages",
                return_value="spa+eng",
            ),
            patch.object(
                ingest,
                "recognize_page",
                return_value=(
                    "ARTICULO 8: Cuatro asignaturas aprobadas."
                ),
            ),
            patch.object(
                ingest,
                "create_embeddings",
                side_effect=lambda texts: [
                    [0.1] * 512 for _ in texts
                ],
            ),
        ):
            _, chunks = ingest.preparar_chunks(
                self.file,
                "general",
            )

        self.assertEqual(
            {c["pagina_inicio"] for c in chunks},
            {1, 2},
        )



class NormalizacionConservadoraTests(unittest.TestCase):

    def test_conserva_porcentajes_y_montos(self):
        original = (
            "Máximo 50% de asignaturas.\\n"
            "Coincidencia mínima 80%.\\n"
            "Costo equivalente al 35%.\\n"
            "Importe Bs 250,50."
        )

        result = ingest.normalize_ocr_text(original)

        self.assertIn("50%", result)
        self.assertIn("80%", result)
        self.assertIn("35%", result)
        self.assertIn("Bs 250,50", result)

    def test_conserva_denominaciones_y_articulos(self):
        original = (
            'Artículo 17. La Universidad Católica '
            'Boliviana “San Pablo” convalidará asignaturas.'
        )

        result = ingest.normalize_pages_text(
            ingest.normalize_page_text_content([
                {
                    "page_number": 5,
                    "text": original,
                }
            ])
        )

        self.assertEqual(result[0]["text"], original)
        self.assertEqual(result[0]["page_number"], 5)

    def test_referencia_de_anexo_no_es_articulo_reglamento(self):
        pages = [
            {
                "page_number": 2,
                "text": (
                    "Artículo 8. Requisitos para traspaso.\\n"
                    "Se requieren cuatro asignaturas aprobadas."
                ),
            },
            {
                "page_number": 3,
                "text": (
                    "Vicerrectorado Académico Nacional\\n"
                    "CIRCULAR VAN 02/2024\\n"
                    "No cobro por traspasos."
                ),
            },
            {
                "page_number": 4,
                "text": (
                    "Resolución N° 131/2023\\n"
                    "En ejercicio de las competencias "
                    "conferidas por el Artículo 81 "
                    "de los Estatutos de la Universidad."
                ),
            },
        ]

        blocks = ingest.split_normative_with_attachments(pages)

        normative = [
            block
            for block in blocks
            if block.get("articulo_numero")
        ]

        self.assertEqual(len(normative), 1)
        self.assertIn("8", normative[0]["articulo_numero"])

        self.assertFalse(
            any(
                "81" in block["articulo_numero"]
                for block in normative
            )
        )

        self.assertTrue(
            any(
                "Artículo 81" in block["content"]
                for block in blocks
            )
        )

if __name__ == "__main__":
    unittest.main()
