from pathlib import Path
import fitz


def load_pdf_text(file_path: Path) -> list[dict]:
    """
    Extrae texto por página desde un PDF.
    Devuelve una lista de diccionarios con:
    - page_number
    - text
    """
    pages = []
    doc = fitz.open(file_path)

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        text = page.get_text("text").strip()

        if text:
            pages.append({
                "page_number": page_index + 1,
                "text": text
            })

    doc.close()
    return pages