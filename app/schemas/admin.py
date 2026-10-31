import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.team import LeaderDetails


# Admin Login
class AdminLoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admin_name: str = Field(..., min_length=1, max_length=256, description="Admin username")
    passcode: str = Field(..., min_length=1, max_length=256, description="Admin secret passcode")


# Admin Login Response with JWT
class AdminLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin_id: uuid.UUID
    role: str = "admin"


# Admin Profile Response
class AdminProfileOut(BaseModel):
    admin_id: uuid.UUID
    admin_name: str
    role: str = "admin"


# Admin Session
class AdminSession(BaseModel):
    admin_id: uuid.UUID
    admin_name: str


# Team Edit by Admin
class TeamUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=256)
    password: str | None = Field(default=None, min_length=6, max_length=256)
    leader_details: LeaderDetails | None = None
    team_members: list[str] | None = None


# Manual Points Adjustment
class PointsAdjust(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delta: int = Field(ge=-10_000, le=10_000)
    reason: str = Field(min_length=1, max_length=255)
