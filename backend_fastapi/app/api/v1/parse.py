from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.user import User
from app.services.document_service import get_document_for_user

router = APIRouter()


@router.post("")
def parse_document(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    doc.vectorization_status = "COMPLETED"
    db.commit()
    return ok({"fileMd5": fileMd5, "vectorizationStatus": "COMPLETED"})
