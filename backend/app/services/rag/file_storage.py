from pathlib import Path
import shutil

from app.core.config import DOCUMENTS_DIR


def save_pdf_file(upload_file) -> dict:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = upload_file.filename
    if not filename:
        raise ValueError("El archivo no tiene nombre.")

    if not filename.lower().endswith(".pdf"):
        raise ValueError("Solo se permiten archivos PDF.")

    destination = DOCUMENTS_DIR / filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    stat = destination.stat()

    return {
        "filename": destination.name,
        "path": str(destination),
        "size_bytes": stat.st_size,
    }


def delete_pdf_file(filename: str) -> bool:
    target = DOCUMENTS_DIR / filename

    if not target.exists() or not target.is_file():
        return False

    target.unlink()
    return True