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
    signature: str | None = None


class InviteCodeRequest(BaseModel):
    code: str
    maxUses: int = Field(default=1, ge=1)
    enabled: bool = True


class RateLimitConfigRequest(BaseModel):
    singleMax: int = Field(default=60, ge=1)
    singleWindowSeconds: int = Field(default=60, ge=1)
    minuteMax: int = Field(default=60, ge=1)
    minuteWindowSeconds: int = Field(default=60, ge=1)
    dayMax: int = Field(default=1000, ge=1)
    dayWindowSeconds: int = Field(default=86400, ge=1)


class ModelProviderRequest(BaseModel):
    scope: str = Field(pattern="^(llm|embedding)$")
    provider: str
    displayName: str
    apiStyle: str = "openai"
    apiBaseUrl: str = ""
    model: str = ""
    apiKey: str = ""
    dimension: int | None = None
    enabled: bool = True
    active: bool = False


class UserOrgAssignRequest(BaseModel):
    userId: int
    orgTags: list[str]
    primaryOrg: str
