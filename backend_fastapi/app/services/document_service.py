from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BizError
from app.core.config import settings
from app.integrations.object_storage import chunk_key, document_key, get_object_storage
from app.integrations.search_index import get_search_index
from app.models.document import Document, DocumentChunk, UploadChunk, UploadTask
from app.models.user import User

SUPPORTED_TYPES = [
    {"extension": ".txt", "mimeType": "text/plain"},
    {"extension": ".md", "mimeType": "text/markdown"},
    {"extension": ".pdf", "mimeType": "application/pdf"},
    {"extension": ".docx", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
]


def _user_orgs(user: User) -> set[str]:
    return {item.tag_id for item in user.org_tags}


def assert_org_access(user: User, org_tag: str) -> None:
    if org_tag not in _user_orgs(user):
        raise BizError("无权访问该组织数据", 403)


def save_chunk(
    db: Session,
    user: User,
    file_md5: str,
    chunk_index: int,
    content: bytes,
    file_name: str,
    total_chunks: int,
    total_size: int,
    org_tag: str | None,
    is_public: bool,
) -> dict:
    org = org_tag or user.primary_org
    assert_org_access(user, org)
    task = db.scalar(select(UploadTask).where(UploadTask.file_md5 == file_md5))
    if not task:
        task = UploadTask(
            file_md5=file_md5,
            file_name=file_name,
            total_chunks=total_chunks,
            total_size=total_size,
            user_id=user.id,
            org_tag=org,
            is_public=is_public,
            status=0,
        )
        db.add(task)
        db.flush()
    elif task.user_id != user.id:
        raise BizError("只有文件所有者可以继续上传", 403)

    chunk = db.scalar(select(UploadChunk).where(UploadChunk.file_md5 == file_md5, UploadChunk.chunk_index == chunk_index))
    stored_content = b"" if settings.object_storage_backend == "minio" else content
    if chunk:
        chunk.content = stored_content
    else:
        db.add(UploadChunk(file_md5=file_md5, chunk_index=chunk_index, content=stored_content))
    if settings.object_storage_backend == "minio":
        get_object_storage().put_bytes(chunk_key(file_md5, chunk_index), content)
    db.commit()
    return upload_status(db, user, file_md5)


def upload_status(db: Session, user: User, file_md5: str) -> dict:
    task = db.scalar(select(UploadTask).where(UploadTask.file_md5 == file_md5))
    if not task:
        return {"fileMd5": file_md5, "uploadedChunks": [], "progress": 0, "status": 0}
    if task.user_id != user.id:
        raise BizError("无权查看该上传任务", 403)
    uploaded = db.scalars(select(UploadChunk.chunk_index).where(UploadChunk.file_md5 == file_md5).order_by(UploadChunk.chunk_index)).all()
    progress = int(len(uploaded) * 100 / task.total_chunks) if task.total_chunks else 0
    return _serialize_task(task, uploaded, progress)


def merge_file(db: Session, user: User, file_md5: str, file_name: str, total_chunks: int, total_size: int, org_tag: str | None, is_public: bool) -> dict:
    org = org_tag or user.primary_org
    assert_org_access(user, org)
    task = db.scalar(select(UploadTask).where(UploadTask.file_md5 == file_md5))
    if not task:
        raise BizError("上传任务不存在", 404)
    if task.user_id != user.id:
        raise BizError("只有文件所有者可以发起合并", 403)
    if task.status == 1:
        return _serialize_document(db.scalar(select(Document).where(Document.file_md5 == file_md5)))
    if task.status == 2:
        raise BizError("文件正在合并中", 409)

    chunks = db.scalars(select(UploadChunk).where(UploadChunk.file_md5 == file_md5).order_by(UploadChunk.chunk_index)).all()
    if len(chunks) != total_chunks:
        raise BizError("分片未上传完整", 400)

    task.status = 2
    db.flush()
    raw = b"".join(_read_chunk_bytes(chunk) for chunk in chunks)
    text = raw.decode("utf-8", errors="ignore")
    object_key = document_key(file_md5, file_name)
    if settings.object_storage_backend == "minio":
        get_object_storage().put_bytes(object_key, raw)
    document = db.scalar(select(Document).where(Document.file_md5 == file_md5))
    if not document:
        document = Document(
            file_md5=file_md5,
            file_name=file_name,
            object_key=object_key,
            content=text,
            user_id=user.id,
            org_tag=org,
            is_public=is_public,
            vectorization_status="COMPLETED",
        )
        db.add(document)
    task.status = 1
    task.merged_at = datetime.utcnow()
    task.vectorization_status = "COMPLETED"
    indexed_chunks = _rebuild_chunks(db, file_md5, text, file_name, user.id, org, is_public)
    if settings.search_backend == "elasticsearch":
        get_search_index().index_chunks(indexed_chunks)
    db.commit()
    return _serialize_document(document)


def read_document_bytes(doc: Document) -> bytes:
    if settings.object_storage_backend == "minio":
        return get_object_storage().get_bytes(doc.object_key)
    return doc.content.encode("utf-8")


def _read_chunk_bytes(chunk: UploadChunk) -> bytes:
    if settings.object_storage_backend == "minio":
        return get_object_storage().get_bytes(chunk_key(chunk.file_md5, chunk.chunk_index))
    return chunk.content


def _rebuild_chunks(db: Session, file_md5: str, text: str, file_name: str, user_id: int, org_tag: str, is_public: bool) -> list[dict]:
    # 这里先按固定窗口模拟解析切块，后续接入真实解析器和 Embedding 服务。
    indexed_chunks = []
    for index, start in enumerate(range(0, max(len(text), 1), 800)):
        part = text[start : start + 800] or ""
        db.add(DocumentChunk(file_md5=file_md5, chunk_id=index, text_content=part, page_number=1, anchor_text=f"chunk-{index}"))
        indexed_chunks.append(
            {
                "fileMd5": file_md5,
                "chunkId": index,
                "textContent": part,
                "pageNumber": 1,
                "anchorText": f"chunk-{index}",
                "fileName": file_name,
                "userId": user_id,
                "orgTag": org_tag,
                "isPublic": is_public,
            }
        )
    return indexed_chunks


def accessible_documents(db: Session, user: User) -> list[dict]:
    orgs = _user_orgs(user)
    docs = db.scalars(
        select(Document).where(
            Document.deleted.is_(False),
            or_(Document.user_id == user.id, Document.is_public.is_(True), Document.org_tag.in_(orgs)),
        )
    ).all()
    return [_serialize_document(doc) for doc in docs]


def get_document_for_user(db: Session, user: User, file_md5: str) -> Document:
    doc = db.scalar(select(Document).where(Document.file_md5 == file_md5, Document.deleted.is_(False)))
    if not doc:
        raise BizError("文档不存在", 404)
    if doc.user_id != user.id and not doc.is_public and doc.org_tag not in _user_orgs(user):
        raise BizError("无权访问该文档", 403)
    return doc


def search_documents(db: Session, user: User, query: str, top_k: int) -> list[dict]:
    orgs = _user_orgs(user)
    if settings.search_backend == "elasticsearch":
        return get_search_index().search(query, user.id, list(orgs), top_k)
    rows = db.scalars(
        select(DocumentChunk)
        .join(Document, Document.file_md5 == DocumentChunk.file_md5)
        .where(
            Document.deleted.is_(False),
            DocumentChunk.text_content.contains(query),
            or_(Document.user_id == user.id, Document.is_public.is_(True), Document.org_tag.in_(orgs)),
        )
        .limit(top_k)
    ).all()
    results = []
    for row in rows:
        doc = db.scalar(select(Document).where(Document.file_md5 == row.file_md5))
        results.append(
            {
                "fileMd5": row.file_md5,
                "chunkId": row.chunk_id,
                "textContent": row.text_content,
                "score": 1.0,
                "fileName": doc.file_name,
                "userId": doc.user_id,
                "orgTag": doc.org_tag,
                "isPublic": doc.is_public,
                "pageNumber": row.page_number,
                "anchorText": row.anchor_text,
                "retrievalMode": "keyword",
                "matchedChunkText": row.text_content,
            }
        )
    return results


def _serialize_task(task: UploadTask, uploaded_chunks: list[int], progress: int) -> dict:
    return {
        "fileMd5": task.file_md5,
        "fileName": task.file_name,
        "userId": task.user_id,
        "orgTag": task.org_tag,
        "public": task.is_public,
        "isPublic": task.is_public,
        "uploadedChunks": uploaded_chunks,
        "progress": progress,
        "status": task.status,
        "vectorizationStatus": task.vectorization_status,
        "vectorizationErrorMessage": task.vectorization_error_message,
        "createdAt": task.created_at.isoformat() if task.created_at else None,
        "mergedAt": task.merged_at.isoformat() if task.merged_at else None,
    }


def _serialize_document(doc: Document | None) -> dict:
    if not doc:
        return {}
    return {
        "fileMd5": doc.file_md5,
        "fileName": doc.file_name,
        "userId": doc.user_id,
        "orgTag": doc.org_tag,
        "public": doc.is_public,
        "isPublic": doc.is_public,
        "vectorizationStatus": doc.vectorization_status,
        "createdAt": doc.created_at.isoformat() if doc.created_at else None,
        "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None,
    }
