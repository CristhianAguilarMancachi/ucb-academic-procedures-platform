from pathlib import Path
import re
import fitz


def clean_text(text: str) -> str:
    """
    Limpieza básica de texto extraído desde PDF.
    """
    if not text:
        return ""

    # Unificar saltos de línea y espacios
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)

    # Eliminar muchas líneas vacías seguidas
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Quitar espacios al inicio/final de líneas
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Quitar espacios extra finales
    text = re.sub(r"[ \t]+", " ", text).strip()

    return text


def load_pdf_text(file_path: Path) -> list[dict]:
    """
    Extrae texto por página desde un PDF y aplica limpieza básica.
    Devuelve una lista de diccionarios con:
    - page_number
    - text
    """
    pages = []
    doc = fitz.open(file_path)

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        text = page.get_text("text")
        text = clean_text(text)

        if text:
            pages.append({
                "page_number": page_index + 1,
                "text": text
            })

    doc.close()
    return pages