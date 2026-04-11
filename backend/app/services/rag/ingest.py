from pathlib import Path
from uuid import uuid4

from app.core.config import DOCUMENTS_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.utils.file_loader import load_pdf_text
from app.utils.text_splitter import split_text
from app.services.rag.embeddings import generate_embeddings
from app.services.rag.vector_store import get_or_create_collection


def ingest_pdf(file_path: Path) -> int:
    collection = get_or_create_collection()
    pages = load_pdf_text(file_path)

    documents = []
    metadatas = []
    ids = []

    for page_data in pages:
        page_number = page_data["page_number"]
        text = page_data["text"]

        chunks = split_text(
            text=text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        for chunk_index, chunk in enumerate(chunks, start=1):
            documents.append(chunk)
            metadatas.append({
                "source": file_path.name,
                "page": page_number,
                "chunk_index": chunk_index
            })
            ids.append(str(uuid4()))

    if not documents:
        return 0

    embeddings = generate_embeddings(documents)

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings
    )

    return len(documents)


def ingest_all_pdfs() -> int:
    total_chunks = 0

    for file_path in DOCUMENTS_DIR.glob("*.pdf"):
        total_chunks += ingest_pdf(file_path)

    return total_chunks


if __name__ == "__main__":
    total = ingest_all_pdfs()
    print(f"Total de chunks indexados: {total}")