from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat.chat import RagChatQueryRequest, RagChatQueryResponse
from app.services.chat.history_service import (
    build_conversation_history,
    get_or_create_chat_session,
    save_chat_message,
)
from app.services.rag.pipeline import run_rag_pipeline

router = APIRouter(tags=["RAG"])

@router.post("/query", response_model=RagChatQueryResponse)
def query_rag(payload: RagChatQueryRequest, db: Session = Depends(get_db)):
    session = get_or_create_chat_session(
        db=db,
        session_id=payload.session_id,
    )

    conversation_history = build_conversation_history(
        db=db,
        session_id=session.id_session,
        limit=8
    )

    result = run_rag_pipeline(
        db=db,
        question=payload.question,
        conversation_history=conversation_history,
    )

    save_chat_message(
        db=db,
        session_id=session.id_session,
        role="user",
        content=payload.question,
    )

    save_chat_message(
        db=db,
        session_id=session.id_session,
        role="assistant",
        content=result["answer"],
        sources_json=result["sources"],
    )

    return RagChatQueryResponse(
        session_id=session.id_session,
        question=result["question"],
        standalone_question=result.get("standalone_question"),
        answer=result["answer"],
        sources=result["sources"],
    )