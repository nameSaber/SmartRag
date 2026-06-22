from pydantic import BaseModel, Field


class OrgTagUpsertRequest(BaseModel):
    tagId: str
    name: str
    description: str = ""
    parentTag: str | None = None
    uploadMaxSizeBytes: int = 104857600


class TokenGrantRequest(BaseModel):
    userId: int
    tokenType: str = Field(pattern="^(LLM|EMBEDDING)$")
    amount: int = Field(gt=0)
    reason: str = "管理员增发"


class RechargePackageRequest(BaseModel):
    packageName: str
    packagePrice: int = Field(ge=0)
    packageDesc: str = ""
    packageBenefit: str = ""
    llmToken: int = 0
    embeddingToken: int = 0
    enabled: bool = True
    sortOrder: int = 0


class CreateOrderRequest(BaseModel):
    packageId: int


class PayCallbackRequest(BaseModel):
    tradeNo: str
    transactionId: str | None = None
    status: str = "SUCCEED"

