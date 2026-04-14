from fastapi import APIRouter, HTTPException, UploadFile, File

from app.schemas.rag import (
    RagQueryRequest,
    RagQueryResponse,
    RagDocumentsResponse,
    RagReingestResponse,
    RagUploadResponse,
    RagDeleteResponse,
    RagTramitesResponse,
)
from app.services.rag.pipeline import run_rag_pipeline
from app.services.rag.document_manager import list_pdf_documents
from app.services.rag.ingest import ingest_all_pdfs
from app.services.rag.file_storage import save_pdf_file, delete_pdf_file
from app.services.rag.tramites_catalog import get_tramites_catalog, get_tramite_by_id

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RagQueryResponse)
def query_rag(payload: RagQueryRequest):
    try:
        if payload.selected_tramite:
            tramite = get_tramite_by_id(payload.selected_tramite)
            if not tramite:
                raise HTTPException(status_code=400, detail="El trámite seleccionado no existe.")

        result = run_rag_pipeline(
            question=payload.question,
            selected_tramite=payload.selected_tramite
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar el módulo RAG: {str(e)}")


@router.get("/tramites", response_model=RagTramitesResponse)
def get_rag_tramites():
    try:
        tramites = get_tramites_catalog()
        return {
            "total_tramites": len(tramites),
            "tramites": tramites,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar trámites: {str(e)}")


@router.get("/documents", response_model=RagDocumentsResponse)
def get_rag_documents():
    try:
        documents = list_pdf_documents()
        return {
            "total_documents": len(documents),
            "documents": documents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar documentos: {str(e)}")


@router.post("/reingest", response_model=RagReingestResponse)
def reingest_rag_documents():
    try:
        result = ingest_all_pdfs(reset_vectorstore=True)
        return {
            "message": "Reingesta completada correctamente.",
            "indexed_files": result["indexed_files"],
            "total_chunks": result["total_chunks"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reingestar documentos: {str(e)}")


@router.post("/upload", response_model=RagUploadResponse)
def upload_rag_document(file: UploadFile = File(...)):
    try:
        document = save_pdf_file(file)
        return {
            "message": "Documento cargado correctamente.",
            "document": document,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir documento: {str(e)}")


@router.delete("/documents/{filename}", response_model=RagDeleteResponse)
def delete_rag_document(filename: str):
    try:
        deleted = delete_pdf_file(filename)

        if not deleted:
            raise HTTPException(status_code=404, detail="Documento no encontrado.")

        return {
            "message": "Documento eliminado correctamente.",
            "filename": filename,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar documento: {str(e)}")