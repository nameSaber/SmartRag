from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.user import User
from app.schemas.document import MergeRequest
from app.services.document_service import SUPPORTED_TYPES, merge_file, save_chunk, upload_status

router = APIRouter()


@router.post("/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    fileMd5: str = Form(...),
    chunkIndex: int = Form(...),
    totalChunks: int = Form(...),
    fileName: str = Form(...),
    totalSize: int = Form(0),
    orgTag: str | None = Form(None),
    isPublic: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = await file.read()
    data = save_chunk(db, current_user, fileMd5, chunkIndex, content, fileName, totalChunks, totalSize, orgTag, isPublic)
    return ok(data)


@router.get("/status")
def status(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(upload_status(db, current_user, fileMd5))


@router.post("/merge")
def merge(payload: MergeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    is_public = payload.public if payload.public is not None else payload.isPublic
    data = merge_file(db, current_user, payload.fileMd5, payload.fileName, payload.totalChunks, payload.totalSize, payload.orgTag, is_public)
    return ok(data)


@router.get("/supported-types")
def supported_types():
    return ok(SUPPORTED_TYPES)

