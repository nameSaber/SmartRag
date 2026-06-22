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
    """接收单个文件分片，并返回当前文件的上传进度。

    前端会按 fileMd5 + chunkIndex 反复调用该接口，服务端需要支持断点续传和重复上传覆盖。
    """
    content = await file.read()
    data = save_chunk(db, current_user, fileMd5, chunkIndex, content, fileName, totalChunks, totalSize, orgTag, isPublic)
    return ok(data)


@router.get("/status")
def status(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """查询指定文件的已上传分片，用于前端恢复上传进度。"""
    return ok(upload_status(db, current_user, fileMd5))


@router.post("/merge")
def merge(payload: MergeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """合并已上传分片，并根据配置进入本地处理或 Kafka 异步处理链路。"""
    is_public = payload.public if payload.public is not None else payload.isPublic
    data = merge_file(db, current_user, payload.fileMd5, payload.fileName, payload.totalChunks, payload.totalSize, payload.orgTag, is_public)
    return ok(data)


@router.get("/supported-types")
def supported_types():
    """返回当前解析器支持的文件类型，供知识库上传页做前置校验。"""
    return ok(SUPPORTED_TYPES)
