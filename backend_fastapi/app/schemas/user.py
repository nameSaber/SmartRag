from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    inviteCode: str | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RefreshTokenRequest(BaseModel):
    refreshToken: str


class PrimaryOrgRequest(BaseModel):
    primaryOrg: str = Field(min_length=1)

