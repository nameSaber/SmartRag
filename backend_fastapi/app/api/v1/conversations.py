from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.user import User
from app.schemas.chat import CreateConversationRequest
from app.services.chat_service import conversation_history, create_session, list_sessions, set_session_status

router = APIRouter()


@router.get("/conversation")
def history(conversationId: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(conversation_history(db, current_user, conversationId))


@router.get("/conversations")
def conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(list_sessions(db, current_user))


@router.post("/conversations")
def create_conversation(payload: CreateConversationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(create_session(db, current_user, payload.title))


@router.put("/conversations/{conversationId}/archive")
def archive(conversationId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(set_session_status(db, current_user, conversationId, "ARCHIVED"))


@router.put("/conversations/{conversationId}/unarchive")
def unarchive(conversationId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(set_session_status(db, current_user, conversationId, "ACTIVE"))


@router.put("/conversations/{conversationId}/switch")
def switch(conversationId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(set_session_status(db, current_user, conversationId, "ACTIVE"))
