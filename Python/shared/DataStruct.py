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
   # location_id: int

    status: Literal["active", "inactive", "completed", "cancelled"] = "active"

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
    event_id: int
    expires_at: str
    max_uploads: int = 50
    purpose: str = "guests"
    is_active: bool = True

class validateToken(BaseModel):
    event_id: int
    token: str

class mediaModel(BaseModel):
    eventID: int
    dataType: str

class eventModify(BaseModel):
    name: str | None = None
    type: str | None = None
    event_date: datetime | None = None

    status: Literal["active", "inactive", "completed", "cancelled", "hide"] | None = None

    # only send this if changing password
    password: str | None = None

    uploads_enabled: bool | None = None
    upload_limit: int | None = Field(default=None, ge=0)


class eventLocationModify(BaseModel):
    venue_name: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None

    searchable: bool | None = None

class tokenReturn(BaseModel):
    access_token: str
    token_type: str = "bearer"

class StoryboardCreateRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    request_id: Optional[int] = None


class StoryboardVideoRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    storyboard_id: int = Field(..., gt=0)
    job_id: Optional[int] = None

class sendWorkMsg():
    job_id: int
    job_type: str
    input_data: str
    prompt_id: str
    event_id: int


