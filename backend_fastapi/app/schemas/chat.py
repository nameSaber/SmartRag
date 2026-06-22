from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    title: str | None = None


class FeedbackRequest(BaseModel):
    rating: str = Field(min_length=1)
    reason: str | None = None
    conversationId: str | None = None
    generationId: str | None = None

