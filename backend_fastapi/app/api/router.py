from fastapi import APIRouter

from app.api.v1 import admin, auth, chat, conversations, documents, parse, recharge, search, upload, users

api_router = APIRouter()
api_router.include_router(users.router, prefix="/api/v1/users", tags=["users"])
api_router.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
api_router.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
api_router.include_router(conversations.router, prefix="/api/v1/users", tags=["conversations"])
api_router.include_router(upload.router, prefix="/api/v1/upload", tags=["upload"])
api_router.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
api_router.include_router(search.router, prefix="/api/v1/search", tags=["search"])
api_router.include_router(parse.router, prefix="/api/v1/parse", tags=["parse"])
api_router.include_router(recharge.router, prefix="/api/v1/recharge", tags=["recharge"])
api_router.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
