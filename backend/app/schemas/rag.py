from pydantic import BaseModel, Field
from typing import Optional


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Pregunta del usuario")
    selected_tramite: Optional[str] = Field(
        default=None,
        description="Identificador del trámite seleccionado en el sistema"
    )


class RagSource(BaseModel):
    document: Optional[str] = None
    page: Optional[int] = None
    article_number: Optional[str] = None
    chunk_strategy: Optional[str] = None


class RagQueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[RagSource]
    selected_tramite: Optional[str] = None


class RagDocumentItem(BaseModel):
    filename: str
    path: str
    size_bytes: int


class RagDocumentsResponse(BaseModel):
    total_documents: int
    documents: list[RagDocumentItem]


class RagReingestResponse(BaseModel):
    message: str
    indexed_files: int
    total_chunks: int


class RagUploadResponse(BaseModel):
    message: str
    document: RagDocumentItem


class RagDeleteResponse(BaseModel):
    message: str
    filename: str


class RagTramiteItem(BaseModel):
    id: str
    label: str
    document_names: list[str]


class RagTramitesResponse(BaseModel):
    total_tramites: int
    tramites: list[RagTramiteItem]