from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError
from app.models.document import Document
from app.models.user import User
from app.services.document_service import rebuild_document_index


def process_file_task(db: Session, payload: dict) -> dict:
    file_md5 = payload["fileMd5"]
    document = db.scalar(select(Document).where(Document.file_md5 == file_md5, Document.deleted.is_(False)))
    if not document:
        raise BizError("文件处理任务对应的文档不存在", 404)
    user = db.get(User, document.user_id)
    if not user:
        raise BizError("文件处理任务对应的用户不存在", 404)
    chunks = rebuild_document_index(db, document, user)
    db.commit()
    return {"fileMd5": file_md5, "chunkCount": len(chunks), "vectorizationStatus": document.vectorization_status}

