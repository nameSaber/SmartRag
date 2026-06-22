from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.user import User
from app.services.document_service import search_documents

router = APIRouter()


@router.get("/hybrid")
def hybrid_search(query: str = Query(...), topK: int = Query(10, ge=1, le=50), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(search_documents(db, current_user, query, topK))

