import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.llm import estimate_tokens, get_llm_gateway
from app.models.chat import ChatFeedback, Conversation, ConversationSession, Generation
from app.models.user import User
from app.services.document_service import search_documents
from app.services.user_service import consume_user_tokens


def create_session(db: Session, user: User, title: str | None = None) -> dict:
    conversation_id = str(uuid4())
    session = ConversationSession(user_id=user.id, conversation_id=conversation_id, title=title or "新会话", status="ACTIVE")
    db.add(session)
    db.commit()
    db.refresh(session)
    return serialize_session(session)


def get_or_create_session(db: Session, user: User, conversation_id: str | None = None, title: str | None = None) -> ConversationSession:
    if conversation_id:
        session = db.scalar(select(ConversationSession).where(ConversationSession.user_id == user.id, ConversationSession.conversation_id == conversation_id))
        if session:
            return session
    data = create_session(db, user, title)
    return db.scalar(select(ConversationSession).where(ConversationSession.conversation_id == data["conversationId"]))


def list_sessions(db: Session, user: User) -> list[dict]:
    rows = db.scalars(select(ConversationSession).where(ConversationSession.user_id == user.id).order_by(ConversationSession.updated_at.desc())).all()
    return [serialize_session(row) for row in rows]


def conversation_history(db: Session, user: User, conversation_id: str | None = None) -> list[dict]:
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if conversation_id:
        stmt = stmt.where(Conversation.conversation_id == conversation_id)
    rows = db.scalars(stmt.order_by(Conversation.timestamp.asc())).all()
    return [
        {
            "id": row.id,
            "conversationId": row.conversation_id,
            "question": row.question,
            "answer": row.answer,
            "referenceMappings": json.loads(row.reference_mappings_json),
            "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        }
        for row in rows
    ]


def set_session_status(db: Session, user: User, conversation_id: str, status: str) -> dict:
    session = get_or_create_session(db, user, conversation_id)
    session.status = status
    db.commit()
    return serialize_session(session)


def generate_answer(db: Session, user: User, question: str, conversation_id: str | None = None) -> dict:
    generation, refs = start_generation(db, user, question, conversation_id)
    answer = get_llm_gateway().generate(question, refs)
    append_generation_content(db, generation.generation_id, answer)
    return complete_generation(db, user, generation.generation_id)


def start_generation(db: Session, user: User, question: str, conversation_id: str | None = None) -> tuple[Generation, list[dict]]:
    session = get_or_create_session(db, user, conversation_id, question[:30] or "新会话")
    refs = search_documents(db, user, question, 3)
    generation = Generation(
        generation_id=str(uuid4()),
        user_id=user.id,
        conversation_id=session.conversation_id,
        question=question,
        status="STREAMING",
        content="",
        reference_mappings_json=json.dumps(refs, ensure_ascii=False),
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation, refs


def append_generation_content(db: Session, generation_id: str, chunk: str) -> dict:
    generation = db.get(Generation, generation_id)
    if not generation:
        raise ValueError("generation not found")
    if generation.status == "CANCELLED":
        return serialize_generation(generation)
    generation.content = (generation.content or "") + chunk
    db.commit()
    db.refresh(generation)
    return serialize_generation(generation)


def complete_generation(db: Session, user: User, generation_id: str) -> dict:
    generation = db.get(Generation, generation_id)
    if not generation or generation.user_id != user.id:
        raise ValueError("generation not found")
    if generation.status == "CANCELLED":
        return serialize_generation(generation)
    refs = json.loads(generation.reference_mappings_json)
    consume_user_tokens(db, user, "LLM", estimate_tokens(generation.question, generation.content), "对话消费", generation_id)
    generation.status = "COMPLETED"
    db.add(
        Conversation(
            user_id=user.id,
            question=generation.question,
            answer=generation.content,
            conversation_id=generation.conversation_id,
            reference_mappings_json=json.dumps(refs, ensure_ascii=False),
        )
    )
    db.commit()
    db.refresh(generation)
    return serialize_generation(generation)


def get_generation(db: Session, user: User, generation_id: str) -> dict | None:
    row = db.get(Generation, generation_id)
    if not row or row.user_id != user.id:
        return None
    return serialize_generation(row)


def cancel_generation(db: Session, user: User, generation_id: str) -> dict | None:
    row = db.get(Generation, generation_id)
    if not row or row.user_id != user.id:
        return None
    row.status = "CANCELLED"
    db.commit()
    db.refresh(row)
    return serialize_generation(row)


def active_generation(db: Session, user: User) -> dict | None:
    row = db.scalar(select(Generation).where(Generation.user_id == user.id, Generation.status == "STREAMING").order_by(Generation.created_at.desc()))
    return serialize_generation(row) if row else None


def save_feedback(db: Session, user: User, rating: str, reason: str | None, conversation_id: str | None, generation_id: str | None) -> None:
    db.add(ChatFeedback(user_id=user.id, rating=rating, reason=reason or "", conversation_id=conversation_id, generation_id=generation_id))
    db.commit()


def serialize_session(row: ConversationSession) -> dict:
    return {
        "id": row.id,
        "conversationId": row.conversation_id,
        "title": row.title,
        "status": row.status,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_generation(row: Generation) -> dict:
    return {
        "generationId": row.generation_id,
        "userId": row.user_id,
        "conversationId": row.conversation_id,
        "question": row.question,
        "status": row.status,
        "content": row.content,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "errorMessage": row.error_message,
        "referenceMappings": json.loads(row.reference_mappings_json),
    }
