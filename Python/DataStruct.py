from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


@dataclass
class uploadResults:
    file_name: str
    status: str
    file_type: str | None = None
    size_bytes: int | None = None
    url: str | None = None
    blob_name: str | None = None
    reason: str | None = None
    content_type: str | None = None

class userCreate(BaseModel):
    user_name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str = "user"
    pwd: str

    @field_validator("user_name", "first_name", "last_name", "email", "pwd", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
    
class userUpdate(BaseModel):
    user_name: str = None
    first_name: str = None
    last_name: str = None
    email: str = None
    phone: str = None
    role: str = None

    @field_validator("user_name", "first_name", "last_name", "email", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        return v.strip() if isinstance(v, str) else v

class userResponse(BaseModel):
    user_id: int
    user_name: str
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str

class userLogin(BaseModel):
    email: Optional[str] = None
    user_name: Optional[str] = None
    pwd: str

    @model_validator(mode="after")
    def require_email_or_username(self):
        if not self.email and not self.user_name:
            raise ValueError("email or user_name is required")
        return self
    
class eventCreate(BaseModel):
    user_id: int
    name: str
    type: str
    event_date: datetime
    location_id: int

    # table default is active
    status: Literal["active", "inactive", "completed", "cancelled"] = "active"

    # Better to accept plain password here, then hash it before DB insert
    password: str

    uploads_enabled: bool = True
    upload_limit: int = Field(default=0, ge=0)

class eventLocation(BaseModel):
    venue_name: str
    street: str
    city: str
    state: str
    zip: str

    searchable: bool = False
    uploads_active: bool = False

class uploadModel(BaseModel):
    eventID: int = Field(..., gt=0)
    userID: Optional[int] = None
    guestID: Optional[int] = None

    @model_validator(mode="after")
    def require_user_or_guest(self):
        if self.userID is None and self.guestID is None:
            raise ValueError("Either userID or guestID is required")
        return self

class PromptRequest(BaseModel):
    eventID: int = Field(..., gt=0)
    userID: int = Field(..., gt=0)
    guestID: int | None = None
    prompt: str = Field(..., min_length=1, max_length=1000)


class MakeVideoRequest(BaseModel):
    eventID: int
    userID: int
    feeling: str
 
    
class QRRequest(BaseModel):
    eventID: int
    expirationDate: str
    maxUploads: int = 50
    purpose: str = "guests"
    is_active: bool = True

class validateToken(BaseModel):
    token: str

class mediaModel(BaseModel):
    eventID: int
    dataType: str