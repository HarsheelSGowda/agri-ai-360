from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_farmer
from app.database.session import get_db
from app.models.farm import Farm
from app.models.prediction import ChatMessage, ChatSession
from app.models.user import Farmer
from app.schemas.assistant_schema import (
    AssistantAskRequest,
    AssistantAskResponse,
    AssistantHistoryResponse,
    AssistantMessageOut,
)
from app.services import market_price_service
from app.services.assistant_service import SUGGESTED_QUESTIONS, answer_question, gather_context

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _to_out(m: ChatMessage) -> AssistantMessageOut:
    return AssistantMessageOut(role=m.role, content=m.content, created_at=m.created_at.isoformat())


def _latest_session(db: Session, farmer: Farmer) -> ChatSession | None:
    return db.query(ChatSession).filter(ChatSession.farmer_id == farmer.id).order_by(ChatSession.created_at.desc()).first()


@router.get("/messages", response_model=AssistantHistoryResponse)
def get_messages(db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    session = _latest_session(db, farmer)
    if not session:
        return AssistantHistoryResponse(session_id=None, messages=[])
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc()).all()
    return AssistantHistoryResponse(session_id=session.id, messages=[_to_out(m) for m in messages])


@router.post("/reset", response_model=AssistantHistoryResponse)
def reset_session(db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    session = ChatSession(farmer_id=farmer.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return AssistantHistoryResponse(session_id=session.id, messages=[])


@router.post("/ask", response_model=AssistantAskResponse)
def ask(payload: AssistantAskRequest, db: Session = Depends(get_db), farmer: Farmer = Depends(get_current_farmer)):
    farm: Farm | None = None
    if payload.farm_id is not None:
        farm = db.query(Farm).filter(Farm.id == payload.farm_id, Farm.farmer_id == farmer.id).first()
        if not farm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    session = _latest_session(db, farmer)
    if not session:
        session = ChatSession(farmer_id=farmer.id)
        db.add(session)
        db.flush()

    db.add(ChatMessage(session_id=session.id, role="farmer", content=payload.message))

    context = gather_context(db, farm, farmer)
    known_crops = market_price_service.list_crops(db)
    answer_text, used_data = answer_question(db, payload.message, context, known_crops)

    reply = ChatMessage(session_id=session.id, role="ai", content=answer_text)
    db.add(reply)
    db.commit()
    db.refresh(reply)

    return AssistantAskResponse(
        session_id=session.id,
        reply=_to_out(reply),
        used_data=used_data,
        suggested_questions=SUGGESTED_QUESTIONS,
    )
