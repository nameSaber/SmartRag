from pydantic import BaseModel, Field


class MergeRequest(BaseModel):
    fileMd5: str
    fileName: str
    totalChunks: int = Field(ge=1)
    totalSize: int = 0
    orgTag: str | None = None
    isPublic: bool = False
    public: bool | None = None


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    topK: int = Field(default=10, ge=1, le=50)

