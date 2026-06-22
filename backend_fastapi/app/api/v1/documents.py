from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.responses import ok
from app.models.user import User
from app.services.document_service import accessible_documents, get_document_for_user

router = APIRouter()


@router.get("/accessible")
def accessible(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(accessible_documents(db, current_user))


@router.get("/uploads")
def uploads(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = accessible_documents(db, current_user)
    return ok({"content": docs, "totalElements": len(docs), "totalPages": 1, "number": 0, "size": len(docs), "first": True, "last": True, "empty": len(docs) == 0})


@router.get("/download")
def download(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    return Response(content=doc.content.encode("utf-8"), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{doc.file_name}"'})


@router.get("/download-by-md5")
def download_by_md5(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return download(fileMd5, current_user, db)


@router.get("/preview")
def preview(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    return ok({"fileMd5": doc.file_md5, "fileName": doc.file_name, "content": doc.content})


@router.get("/page-preview")
def page_preview(fileMd5: str, page: int = Query(1, ge=1), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    return ok({"fileMd5": doc.file_md5, "page": page, "content": doc.content})


@router.get("/reference-detail")
def reference_detail(fileMd5: str, chunkId: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    return ok({"fileMd5": doc.file_md5, "chunkId": chunkId, "fileName": doc.file_name, "textContent": doc.content})


@router.delete("/{fileMd5}")
def delete_document(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    if doc.user_id != current_user.id:
        from app.core.exceptions import BizError

        raise BizError("只有文档所有者可以删除", 403)
    doc.deleted = True
    db.commit()
    return ok(None)


@router.post("/{fileMd5}/reindex")
def reindex(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_document_for_user(db, current_user, fileMd5)
    doc.vectorization_status = "COMPLETED"
    db.commit()
    return ok({"fileMd5": fileMd5, "vectorizationStatus": "COMPLETED"})


@router.post("/{fileMd5}/vectorization/retry")
def retry_vectorization(fileMd5: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return reindex(fileMd5, current_user, db)

