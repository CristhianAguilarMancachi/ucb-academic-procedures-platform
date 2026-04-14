from pathlib import Path

from app.core.config import DOCUMENTS_DIR


def list_pdf_documents() -> list[dict]:
    documents = []

    for file_path in sorted(DOCUMENTS_DIR.glob("*.pdf")):
        stat = file_path.stat()
        documents.append({
            "filename": file_path.name,
            "path": str(file_path),
            "size_bytes": stat.st_size,
        })

    return documents