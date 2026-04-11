import chromadb
from chromadb.config import Settings
from app.core.config import VECTORSTORE_DIR

COLLECTION_NAME = "academic_procedures_documents"


def get_chroma_client():
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(VECTORSTORE_DIR),
        settings=Settings(anonymized_telemetry=False)
    )


def get_or_create_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)