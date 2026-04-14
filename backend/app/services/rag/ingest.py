from pathlib import Path
from uuid import uuid4
import shutil

from app.core.config import DOCUMENTS_DIR, CHUNK_SIZE, CHUNK_OVERLAP, VECTORSTORE_DIR
from app.utils.file_loader import load_pdf_text
from app.utils.text_splitter import split_text
from app.services.rag.embeddings import generate_embeddings
from app.services.rag.vector_store import get_or_create_collection


def build_metadata(file_path: Path, page_number: int, chunk_index: int, chunk_data: dict) -> dict:
    metadata = {
        "source": file_path.name,
        "page": int(page_number),
        "chunk_index": int(chunk_index),
        "chunk_strategy": str(chunk_data.get("strategy", "unknown")),
    }

    article_number = chunk_data.get("article_number")
    section_title = chunk_data.get("section_title")

    if article_number is not None:
        metadata["article_number"] = str(article_number)

    if section_title is not None:
        metadata["section_title"] = str(section_title)

    return metadata


def clear_vectorstore() -> None:
    if VECTORSTORE_DIR.exists():
        shutil.rmtree(VECTORSTORE_DIR)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


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

        for chunk_index, chunk_data in enumerate(chunks, start=1):
            chunk_text = chunk_data["text"]

            documents.append(chunk_text)
            metadatas.append(
                build_metadata(
                    file_path=file_path,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    chunk_data=chunk_data
                )
            )
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


def ingest_all_pdfs(reset_vectorstore: bool = False) -> dict:
    if reset_vectorstore:
        clear_vectorstore()

    total_chunks = 0
    indexed_files = 0

    for file_path in DOCUMENTS_DIR.glob("*.pdf"):
        chunks_count = ingest_pdf(file_path)
        if chunks_count > 0:
            indexed_files += 1
            total_chunks += chunks_count

    return {
        "indexed_files": indexed_files,
        "total_chunks": total_chunks,
    }


if __name__ == "__main__":
    result = ingest_all_pdfs(reset_vectorstore=True)
    print(
        f"Documentos indexados: {result['indexed_files']} | "
        f"Total de chunks indexados: {result['total_chunks']}"
    )