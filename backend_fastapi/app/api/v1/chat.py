from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.core.exceptions import BizError
from app.core.responses import ok
from app.core.security import create_token, decode_token
from app.models.user import User
from app.schemas.chat import FeedbackRequest
from app.integrations.llm import get_llm_gateway
from app.services.chat_service import active_generation, cancel_generation, generate_answer, get_generation, save_feedback
from app.services.rate_limiter import enforce_rate_limit

router = APIRouter()
ws_router = APIRouter()


@router.get("/websocket-token")
def websocket_token(current_user: User = Depends(get_current_user)):
    cmd_token = create_token(str(current_user.id), "access", current_user.token_version, __import__("datetime").timedelta(minutes=10))
    return ok({"cmdToken": cmd_token})


@router.get("/generation/{generationId}")
def generation_snapshot(generationId: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snapshot = get_generation(db, current_user, generationId)
    if snapshot is None:
        raise BizError("生成任务不存在", 404)
    return ok(snapshot)


@router.get("/active-generation")
def active(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(active_generation(db, current_user))


@router.post("/feedback")
def feedback(payload: FeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    save_feedback(db, current_user, payload.rating, payload.reason, payload.conversationId, payload.generationId)
    return ok(None)


@ws_router.websocket("/chat/{token}")
async def websocket_chat(websocket: WebSocket, token: str):
    await websocket.accept()
    db = SessionLocal()
    try:
        payload = decode_token(token, "access")
        user = db.get(User, int(payload["sub"]))
        if not user or int(payload.get("ver", -1)) != user.token_version:
            await websocket.send_json({"type": "error", "message": "token 已失效"})
            await websocket.close()
            return
        await websocket.send_json({"type": "connected", "message": "连接成功"})
        while True:
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if message.get("type") == "cancel":
                generation_id = message.get("generationId")
                snapshot = cancel_generation(db, user, generation_id) if generation_id else None
                await websocket.send_json({"type": "cancelled", "data": snapshot})
                continue
            question = message.get("message") or message.get("question") or ""
            enforce_rate_limit(db, "chatMessage", str(user.id))
            snapshot = generate_answer(db, user, question, message.get("conversationId"))
            await websocket.send_json({"type": "generation", "data": snapshot})
            for chunk in get_llm_gateway().stream_text(snapshot["content"]):
                await websocket.send_json({"type": "delta", "generationId": snapshot["generationId"], "content": chunk})
            await websocket.send_json({"type": "done", "generationId": snapshot["generationId"]})
    except WebSocketDisconnect:
        return
    finally:
        db.close()
