from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal, Optional, Any
import json
from pydantic import BaseModel, Field, field_validator, model_validator



#user section
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
    
    @field_validator("email")
    @classmethod
    def validate_profile_email(cls, value):
        if value is not None and ("@" not in value or value.startswith("@")):
            raise ValueError("A valid email address is required")

        return value.lower() if value is not None else value
    
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
    
class userProfileUpdate(BaseModel):
    user_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    first_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, min_length=3, max_length=254)
    phone: Optional[str] = Field(default=None, min_length=1, max_length=50)

    @field_validator(
        "user_name",
        "first_name",
        "last_name",
        "email",
        "phone",
        mode="before",
    )
    @classmethod
    def strip_profile_whitespace(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def validate_profile_email(cls, value):
        if value is not None and ("@" not in value or value.startswith("@")):
            raise ValueError("A valid email address is required")

        return value.lower() if value is not None else value

    @model_validator(mode="after")
    def require_profile_change(self):
        if not self.model_dump(exclude_none=True):
            raise ValueError("At least one profile field is required")

        return self
    
class userPasswordUpdate(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=1024)
    new_password: str = Field(..., min_length=8, max_length=1024)

    @model_validator(mode="after")
    def require_new_password(self):
        if self.current_password == self.new_password:
            raise ValueError(
                "The new password must be different from the current password"
            )

        return self

class guestSessionRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    qr_token: str = Field(..., min_length=1, max_length=2048)
    display_name: str = Field(..., min_length=1, max_length=150)
    email: Optional[str] = Field(default=None, max_length=254)
    phone_number: Optional[str] = Field(default=None, max_length=50)

    @field_validator(
        "qr_token",
        "display_name",
        "email",
        "phone_number",
        mode="before",
    )
    @classmethod
    def strip_guest_values(cls, value):
        if not isinstance(value, str):
            return value

        value = value.strip()
        return value or None

    @field_validator("email")
    @classmethod
    def validate_guest_email(cls, value):
        if value is not None and (
            "@" not in value or value.startswith("@")
        ):
            raise ValueError("A valid email address is required")

        return value.lower() if value is not None else value
    
#event section
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

#upload model
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

class uploadModel(BaseModel):
    eventID: int = Field(..., gt=0)
    userID: Optional[int] = None
    guestID: Optional[int] = None

    @model_validator(mode="after")
    def require_user_or_guest(self):
        if self.userID is None and self.guestID is None:
            raise ValueError("Either userID or guestID is required")
        return self

class photoSlideshowAction(BaseModel):
    action: Literal["approve", "exclude"]

class PromptHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=1000)

class PromptRequest(BaseModel):
    eventID: int = Field(..., gt=0)
    userID: int = Field(..., gt=0)
    guestID: int | None = None
    prompt: str = Field(..., min_length=1, max_length=1000)
    history: list[PromptHistoryMessage] = Field(default_factory=list, max_length=10)


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
    user: userResponse

class StoryboardCreateRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    request_id: Optional[int] = None

    
class StoryboardVideoRequest(BaseModel):
    event_id: int = Field(..., gt=0)
    storyboard_id: int = Field(..., gt=0)
    job_id: Optional[int] = None

class sendWorkMsg(BaseModel):
    job_id: int
    job_type: str
    input_data: str
    prompt_id: str
    event_id: int


class ImageRankingData(BaseModel):
    # Use photo_id for photos
    photo_id: int | None = None

    # Existing ranking fields
    caption: str = ""
    mood_label: str = "unknown"
    mood_conf_score: float = Field(default=0.0, ge=0.0)
    all_mood_labels: str = ""
    keyword_score: int = Field(default=0, ge=0, le=100)
    keywords: str = ""
    nudity_check: bool = False
    all_mood_scores: str = ""

    # Category score columns
    romantic: int = Field(default=0, ge=0, le=100)
    professional: int = Field(default=0, ge=0, le=100)
    friends: int = Field(default=0, ge=0, le=100)
    family: int = Field(default=0, ge=0, le=100)
    ceremony: int = Field(default=0, ge=0, le=100)
    reception: int = Field(default=0, ge=0, le=100)
    dancing: int = Field(default=0, ge=0, le=100)
    food_decor: int = Field(default=0, ge=0, le=100)
    venue_detail: int = Field(default=0, ge=0, le=100)

    happy: int = Field(default=0, ge=0, le=100)
    sentimental: int = Field(default=0, ge=0, le=100)
    energetic: int = Field(default=0, ge=0, le=100)
    calm: int = Field(default=0, ge=0, le=100)
    dramatic: int = Field(default=0, ge=0, le=100)
    nostalgic: int = Field(default=0, ge=0, le=100)
    funny: int = Field(default=0, ge=0, le=100)
    general: int = Field(default=0, ge=0, le=100)

    quality_reject: int = Field(default=0, ge=0, le=100)
    nudity: int = Field(default=0, ge=0, le=100)

    matched_keywords: str = ""

    event_type: Literal[
    "wedding",
    "birthday",
    "graduation",
    "concert",
    "sports",
    "corporate",
    "general",
    "unknown"
] = "unknown"
    event_type_conf_score: float = Field(default=0.0,ge=0.0,le=1.0)

    event_detail_label: str = "unknown"

    event_detail_conf_score: float = Field(default=0.0,ge=0.0,le=1.0)

    event_detail_scores: str = ""
    @model_validator(mode="after")
    def require_photo_id(self):
        if self.photo_id is None:
            raise ValueError("Either photo_id or frame_id is required")
        return self

    @field_validator(
    "caption",
    "mood_label",
    "all_mood_labels",
    "keywords",
    "all_mood_scores",
    "matched_keywords",
    "event_detail_scores",
    mode="before"
)
        
    @classmethod
    def convert_to_string(cls, v: Any) -> str:
        if v is None:
            return ""

        if isinstance(v, str):
            return v

        if isinstance(v, list):
            return ",".join(str(item) for item in v)

        if isinstance(v, dict):
            return json.dumps(v)

        return str(v)
    
@dataclass
class StoryboardItemData:
    source_type: str
    photo_id: int | None
    video_id: int | None
    frame_id: int | None

    sequence_order: int
    sequence_group: int

    scene_label: str
    confidence: float
    reason: str | None

    file_path: str | None
    occurred_at: str | None

    time_delta_seconds: float
    days_from_event: float

    clip_start_seconds: float | None
    clip_end_seconds: float | None
    duration_seconds: float

    selection_score: float
    score_breakdown: dict[str, Any]

    @staticmethod
    def optionalInt(value: Any) -> int | None:
        if value is None or value == "":
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def optionalFloat(value: Any) -> float | None:
        if value is None or value == "":
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def requiredFloat(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def parseScoreBreakdown(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except (TypeError, ValueError, json.JSONDecodeError):
                return {}

        return {}

    @classmethod
    def fromRow(cls, row: dict[str, Any]) -> "StoryboardItemData":
        occurredAt = row.get("occurred_at")

        if isinstance(occurredAt, datetime):
            occurredAt = occurredAt.isoformat()
        elif occurredAt is not None:
            occurredAt = str(occurredAt)

        sourceType = str(
            row.get("source_type") or "photo"
        ).strip().lower()

        sceneLabel = row.get("scene_label")
        if sceneLabel is None:
            sceneLabel = ""

        reason = row.get("reason")
        if reason is not None:
            reason = str(reason)

        filePath = row.get("file_path")
        if filePath is not None:
            filePath = str(filePath)

        return cls(
            source_type=sourceType,

            photo_id=cls.optionalInt(row.get("photo_id")),
            video_id=cls.optionalInt(row.get("video_id")),
            frame_id=cls.optionalInt(row.get("frame_id")),

            sequence_order=int(row.get("sequence_order") or 0),
            sequence_group=int(row.get("sequence_group") or 1),

            scene_label=str(sceneLabel),
            confidence=cls.requiredFloat(row.get("confidence")),
            reason=reason,

            file_path=filePath,
            occurred_at=occurredAt,

            time_delta_seconds=cls.requiredFloat(
                row.get("time_delta_seconds")
            ),
            days_from_event=cls.requiredFloat(
                row.get("days_from_event")
            ),

            clip_start_seconds=cls.optionalFloat(
                row.get("clip_start_seconds")
            ),
            clip_end_seconds=cls.optionalFloat(
                row.get("clip_end_seconds")
            ),
            duration_seconds=cls.requiredFloat(
                row.get("duration_seconds")
            ),

            selection_score=cls.requiredFloat(
                row.get("selection_score")
            ),
            score_breakdown=cls.parseScoreBreakdown(
                row.get("score_breakdown")
            ),
        )

    def toDict(self) -> dict[str, Any]:
        return asdict(self)


class EventProfile(BaseModel):
    event_type: Literal[
        "wedding",
        "birthday",
        "graduation",
        "concert",
        "sports",
        "corporate",
        "general",
        "unknown"
    ]

    # Event-specific scenes
    detail_labels: dict[str, list[str]]

    # Caption keywords for event-specific scenes
    detail_keywords: dict[str, dict[str, int]]

    # Event-specific phrases mapped to common mood categories
    mood_labels: dict[str, list[str]]

    # Caption keywords mapped to common scoring columns
    mood_keywords: dict[str, dict[str, int]]

    def get_detail_candidate_labels(self) -> list[str]:
        labels = []

        for categoryLabels in self.detail_labels.values():
            labels.extend(categoryLabels)

        return labels

    def get_detail_label_map(self) -> dict[str, str]:
        labelMap = {}

        for category, labels in self.detail_labels.items():
            for label in labels:
                labelMap[label] = category

        return labelMap

    def get_mood_candidate_labels(self) -> list[str]:
        labels = []

        for categoryLabels in self.mood_labels.values():
            labels.extend(categoryLabels)

        return labels

    def get_mood_label_map(self) -> dict[str, str]:
        labelMap = {}

        for category, labels in self.mood_labels.items():
            for label in labels:
                labelMap[label] = category

        return labelMap
    
EVENT_PROFILES = {
    "wedding": EventProfile(
        event_type="wedding",

        detail_labels={
            "ceremony": [
                "a wedding ceremony photo",
                "a bride walking down the aisle",
                "a groom waiting at the altar",
                "a wedding officiant conducting a ceremony"
            ],

            "vows": [
                "a couple exchanging wedding vows",
                "a bride reading wedding vows",
                "a groom reading wedding vows"
            ],

            "ring_exchange": [
                "a wedding ring exchange",
                "a bride placing a ring on the groom",
                "a groom placing a ring on the bride"
            ],

            "first_kiss": [
                "a newly married couple kissing",
                "a wedding first kiss",
                "a bride and groom kissing at the altar"
            ],

            "first_dance": [
                "a bride and groom having their first dance",
                "a newly married couple slow dancing",
                "a romantic wedding dance"
            ],

            "family": [
                "a wedding family portrait",
                "parents posing with the bride and groom",
                "a family celebrating a wedding"
            ],

            "wedding_party": [
                "a wedding party group photo",
                "a group of bridesmaids",
                "a group of groomsmen"
            ],

            "speech_toast": [
                "a wedding speech",
                "a wedding toast",
                "a guest speaking at a wedding reception"
            ],

            "cake_cutting": [
                "a bride and groom cutting a wedding cake",
                "a wedding cake cutting photo",
                "a couple standing beside a wedding cake"
            ],

            "reception": [
                "a wedding reception party",
                "guests celebrating at a wedding reception",
                "a decorated wedding reception hall"
            ]
        },

        detail_keywords={
            "ceremony": {
                "ceremony": 35,
                "altar": 30,
                "aisle": 25,
                "officiant": 25
            },

            "vows": {
                "vows": 45,
                "exchanging vows": 50
            },

            "ring_exchange": {
                "rings": 30,
                "wedding rings": 40,
                "ring exchange": 50
            },

            "first_kiss": {
                "kiss": 35,
                "kissing": 35,
                "first kiss": 50
            },

            "first_dance": {
                "first dance": 50,
                "slow dancing": 40,
                "dancing together": 35
            },

            "family": {
                "family": 35,
                "parents": 30,
                "family portrait": 45
            },

            "wedding_party": {
                "wedding party": 45,
                "bridesmaids": 40,
                "groomsmen": 40
            },

            "speech_toast": {
                "speech": 35,
                "toast": 35,
                "champagne": 20
            },

            "cake_cutting": {
                "cake cutting": 50,
                "wedding cake": 35
            },

            "reception": {
                "reception": 40,
                "celebration": 25,
                "dance floor": 25
            }
        },
        mood_labels={
    "romantic": [
        "a romantic bride and groom moment",
        "a loving wedding couple",
        "an intimate wedding photograph",
        "a bride and groom holding each other",
        "a romantic wedding kiss"
    ],

    "happy": [
        "a joyful wedding celebration",
        "a happy bride and groom",
        "wedding guests smiling and celebrating",
        "a bride laughing at her wedding",
        "a groom happily celebrating"
    ],

    "sentimental": [
        "an emotional wedding moment",
        "a heartfelt family wedding moment",
        "a touching wedding photograph",
        "a tearful wedding ceremony",
        "an emotional wedding speech"
    ],

    "energetic": [
        "an energetic wedding reception",
        "guests dancing at a wedding",
        "a lively wedding celebration",
        "a crowded wedding dance floor",
        "an exciting wedding party"
    ],

    "calm": [
        "a calm intimate wedding moment",
        "a peaceful wedding portrait",
        "a quiet wedding ceremony",
        "a relaxed bride and groom",
        "a serene wedding photograph"
    ],

    "dramatic": [
        "a dramatic wedding photograph",
        "a cinematic bride and groom portrait",
        "a wedding photo with dramatic lighting",
        "an intense emotional wedding moment",
        "a bold artistic wedding portrait"
    ],

    "nostalgic": [
        "a timeless wedding memory",
        "a nostalgic wedding photograph",
        "a classic bride and groom portrait",
        "a traditional family wedding moment",
        "a wedding photo that feels like a memory"
    ],

    "funny": [
        "a funny wedding reaction",
        "a humorous wedding candid",
        "a silly wedding party photograph",
        "wedding guests laughing together",
        "a playful bride and groom"
    ],

    "general": [
        "a general wedding photograph",
        "a normal wedding event photo",
        "people attending a wedding",
        "a standard wedding celebration photo"
    ]
},

mood_keywords={
    "romantic": {
        "kiss": 35,
        "kissing": 35,
        "first kiss": 50,
        "holding hands": 35,
        "hand in hand": 35,
        "first dance": 45,
        "slow dancing": 35,
        "embracing": 30,
        "bride and groom": 40,
        "newlyweds": 40,
        "romantic": 40,
        "intimate": 30,
        "loving": 30,
        "couple": 25
    },

    "professional": {
        "professional portrait": 45,
        "formal portrait": 40,
        "wedding portrait": 40,
        "bride portrait": 40,
        "groom portrait": 40,
        "couple portrait": 40,
        "family portrait": 35,
        "group portrait": 30,
        "posed": 25,
        "looking at the camera": 25
    },

    "friends": {
        "friends": 35,
        "wedding party": 45,
        "bridesmaids": 40,
        "groomsmen": 40,
        "group of friends": 40,
        "guests": 20,
        "group photo": 25
    },

    "family": {
        "family": 35,
        "parents": 30,
        "mother": 20,
        "father": 20,
        "grandparents": 30,
        "family portrait": 45,
        "father daughter": 40,
        "mother son": 40
    },

    "ceremony": {
        "ceremony": 40,
        "wedding ceremony": 50,
        "altar": 35,
        "aisle": 30,
        "officiant": 30,
        "vows": 45,
        "exchanging vows": 50,
        "ring exchange": 50
    },

    "reception": {
        "reception": 45,
        "wedding reception": 50,
        "toast": 30,
        "speech": 30,
        "cake cutting": 40,
        "champagne": 25,
        "banquet": 25,
        "celebration": 25
    },

    "dancing": {
        "dance": 25,
        "dancing": 35,
        "first dance": 50,
        "slow dancing": 40,
        "dance floor": 45,
        "guests dancing": 40,
        "couple dancing": 40
    },

    "food_decor": {
        "wedding cake": 40,
        "cake": 25,
        "flowers": 25,
        "bouquet": 30,
        "centerpiece": 30,
        "candles": 25,
        "decorations": 30,
        "table setting": 25
    },

    "venue_detail": {
        "wedding venue": 45,
        "venue": 35,
        "reception hall": 40,
        "ballroom": 35,
        "chapel": 30,
        "church": 30,
        "decorated room": 30,
        "garden": 25
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "laughing": 30,
        "joyful": 40,
        "celebrating": 30,
        "cheering": 30,
        "excited": 25
    },

    "sentimental": {
        "sentimental": 40,
        "emotional": 40,
        "heartfelt": 40,
        "touching": 35,
        "tearful": 30,
        "happy tears": 40,
        "special moment": 30
    },

    "energetic": {
        "energetic": 40,
        "party": 25,
        "dancing": 35,
        "cheering": 30,
        "crowd": 20,
        "lively": 40,
        "exciting": 30
    },

    "calm": {
        "calm": 40,
        "peaceful": 40,
        "quiet": 30,
        "relaxed": 30,
        "gentle": 25,
        "serene": 40,
        "soft light": 25
    },

    "dramatic": {
        "dramatic": 45,
        "cinematic": 40,
        "spotlight": 35,
        "silhouette": 35,
        "high contrast": 30,
        "moody": 35,
        "artistic": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "timeless": 40,
        "classic": 35,
        "traditional": 30,
        "memory": 35,
        "black and white": 25
    },

    "funny": {
        "funny": 45,
        "silly": 40,
        "goofy": 40,
        "humorous": 40,
        "playful": 30,
        "laughing": 25,
        "making faces": 35
    },

    "general": {
        "wedding": 15,
        "event": 10,
        "guest": 10,
        "people": 10,
        "group": 10
    }
}
    ),

    "birthday": EventProfile(
        event_type="birthday",

        detail_labels={
            "birthday_person": [
                "a person celebrating their birthday",
                "a birthday portrait",
                "a birthday guest of honor"
            ],

            "candles": [
                "a person blowing out birthday candles",
                "birthday candles on a cake",
                "a person making a birthday wish"
            ],

            "birthday_cake": [
                "a decorated birthday cake",
                "a birthday cake being cut",
                "a person standing beside a birthday cake"
            ],

            "gifts": [
                "a person opening birthday gifts",
                "wrapped birthday presents",
                "a birthday gift table"
            ],

            "friends": [
                "friends celebrating a birthday",
                "a birthday group photo with friends",
                "friends smiling at a birthday party"
            ],

            "family": [
                "a family birthday celebration",
                "a birthday family portrait",
                "family members at a birthday party"
            ],

            "decorations": [
                "birthday balloons and decorations",
                "a decorated birthday party room",
                "a birthday banner and balloons"
            ],

            "party": [
                "a lively birthday party",
                "people dancing at a birthday party",
                "birthday guests celebrating"
            ]
        },

        detail_keywords={
            "birthday_person": {
                "birthday": 30,
                "guest of honor": 40
            },

            "candles": {
                "candles": 35,
                "blowing out candles": 50,
                "making a wish": 40
            },

            "birthday_cake": {
                "birthday cake": 45,
                "cake": 25
            },

            "gifts": {
                "gift": 30,
                "gifts": 35,
                "presents": 35,
                "opening presents": 45
            },

            "friends": {
                "friends": 40,
                "group of friends": 45
            },

            "family": {
                "family": 40,
                "parents": 25,
                "children": 20
            },

            "decorations": {
                "balloons": 35,
                "birthday banner": 40,
                "decorations": 25
            },

            "party": {
                "party": 30,
                "celebrating": 30,
                "dancing": 25
            }
        },
        mood_labels={
    "romantic": [
        "a romantic bride and groom moment",
        "a loving wedding couple",
        "an intimate wedding photograph",
        "a bride and groom holding each other",
        "a romantic wedding kiss"
    ],

    "happy": [
        "a joyful wedding celebration",
        "a happy bride and groom",
        "wedding guests smiling and celebrating",
        "a bride laughing at her wedding",
        "a groom happily celebrating"
    ],

    "sentimental": [
        "an emotional wedding moment",
        "a heartfelt family wedding moment",
        "a touching wedding photograph",
        "a tearful wedding ceremony",
        "an emotional wedding speech"
    ],

    "energetic": [
        "an energetic wedding reception",
        "guests dancing at a wedding",
        "a lively wedding celebration",
        "a crowded wedding dance floor",
        "an exciting wedding party"
    ],

    "calm": [
        "a calm intimate wedding moment",
        "a peaceful wedding portrait",
        "a quiet wedding ceremony",
        "a relaxed bride and groom",
        "a serene wedding photograph"
    ],

    "dramatic": [
        "a dramatic wedding photograph",
        "a cinematic bride and groom portrait",
        "a wedding photo with dramatic lighting",
        "an intense emotional wedding moment",
        "a bold artistic wedding portrait"
    ],

    "nostalgic": [
        "a timeless wedding memory",
        "a nostalgic wedding photograph",
        "a classic bride and groom portrait",
        "a traditional family wedding moment",
        "a wedding photo that feels like a memory"
    ],

    "funny": [
        "a funny wedding reaction",
        "a humorous wedding candid",
        "a silly wedding party photograph",
        "wedding guests laughing together",
        "a playful bride and groom"
    ],

    "general": [
        "a general wedding photograph",
        "a normal wedding event photo",
        "people attending a wedding",
        "a standard wedding celebration photo"
    ]
},

mood_keywords={
    "romantic": {
        "kiss": 35,
        "kissing": 35,
        "first kiss": 50,
        "holding hands": 35,
        "hand in hand": 35,
        "first dance": 45,
        "slow dancing": 35,
        "embracing": 30,
        "bride and groom": 40,
        "newlyweds": 40,
        "romantic": 40,
        "intimate": 30,
        "loving": 30,
        "couple": 25
    },

    "professional": {
        "professional portrait": 45,
        "formal portrait": 40,
        "wedding portrait": 40,
        "bride portrait": 40,
        "groom portrait": 40,
        "couple portrait": 40,
        "family portrait": 35,
        "group portrait": 30,
        "posed": 25,
        "looking at the camera": 25
    },

    "friends": {
        "friends": 35,
        "wedding party": 45,
        "bridesmaids": 40,
        "groomsmen": 40,
        "group of friends": 40,
        "guests": 20,
        "group photo": 25
    },

    "family": {
        "family": 35,
        "parents": 30,
        "mother": 20,
        "father": 20,
        "grandparents": 30,
        "family portrait": 45,
        "father daughter": 40,
        "mother son": 40
    },

    "ceremony": {
        "ceremony": 40,
        "wedding ceremony": 50,
        "altar": 35,
        "aisle": 30,
        "officiant": 30,
        "vows": 45,
        "exchanging vows": 50,
        "ring exchange": 50
    },

    "reception": {
        "reception": 45,
        "wedding reception": 50,
        "toast": 30,
        "speech": 30,
        "cake cutting": 40,
        "champagne": 25,
        "banquet": 25,
        "celebration": 25
    },

    "dancing": {
        "dance": 25,
        "dancing": 35,
        "first dance": 50,
        "slow dancing": 40,
        "dance floor": 45,
        "guests dancing": 40,
        "couple dancing": 40
    },

    "food_decor": {
        "wedding cake": 40,
        "cake": 25,
        "flowers": 25,
        "bouquet": 30,
        "centerpiece": 30,
        "candles": 25,
        "decorations": 30,
        "table setting": 25
    },

    "venue_detail": {
        "wedding venue": 45,
        "venue": 35,
        "reception hall": 40,
        "ballroom": 35,
        "chapel": 30,
        "church": 30,
        "decorated room": 30,
        "garden": 25
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "laughing": 30,
        "joyful": 40,
        "celebrating": 30,
        "cheering": 30,
        "excited": 25
    },

    "sentimental": {
        "sentimental": 40,
        "emotional": 40,
        "heartfelt": 40,
        "touching": 35,
        "tearful": 30,
        "happy tears": 40,
        "special moment": 30
    },

    "energetic": {
        "energetic": 40,
        "party": 25,
        "dancing": 35,
        "cheering": 30,
        "crowd": 20,
        "lively": 40,
        "exciting": 30
    },

    "calm": {
        "calm": 40,
        "peaceful": 40,
        "quiet": 30,
        "relaxed": 30,
        "gentle": 25,
        "serene": 40,
        "soft light": 25
    },

    "dramatic": {
        "dramatic": 45,
        "cinematic": 40,
        "spotlight": 35,
        "silhouette": 35,
        "high contrast": 30,
        "moody": 35,
        "artistic": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "timeless": 40,
        "classic": 35,
        "traditional": 30,
        "memory": 35,
        "black and white": 25
    },

    "funny": {
        "funny": 45,
        "silly": 40,
        "goofy": 40,
        "humorous": 40,
        "playful": 30,
        "laughing": 25,
        "making faces": 35
    },

    "general": {
        "wedding": 15,
        "event": 10,
        "guest": 10,
        "people": 10,
        "group": 10
    }
}
    ),

    "graduation": EventProfile(
        event_type="graduation",

        detail_labels={
            "cap_and_gown": [
                "a graduate wearing a cap and gown",
                "graduates wearing graduation robes",
                "a graduation portrait"
            ],

            "diploma": [
                "a graduate holding a diploma",
                "a student receiving a diploma",
                "a graduation certificate presentation"
            ],

            "stage": [
                "a graduate walking across a stage",
                "a student at a graduation podium",
                "a commencement stage"
            ],

            "commencement": [
                "a graduation commencement ceremony",
                "graduates seated at a commencement ceremony",
                "a graduation speaker addressing students"
            ],

            "family": [
                "a graduate celebrating with family",
                "a graduation family portrait",
                "parents posing with a graduate"
            ],

            "friends": [
                "graduates celebrating together",
                "graduation friends posing together",
                "a group of graduating students"
            ],

            "celebration": [
                "a graduation party",
                "a graduate celebrating an achievement",
                "people cheering for a graduate"
            ]
        },

        detail_keywords={
            "cap_and_gown": {
                "cap and gown": 50,
                "graduation gown": 45,
                "graduate": 25
            },

            "diploma": {
                "diploma": 50,
                "certificate": 35
            },

            "stage": {
                "stage": 30,
                "podium": 35,
                "walking across": 35
            },

            "commencement": {
                "commencement": 50,
                "graduation ceremony": 45
            },

            "family": {
                "family": 35,
                "parents": 30
            },

            "friends": {
                "graduates": 30,
                "friends": 35,
                "students": 20
            },

            "celebration": {
                "celebration": 30,
                "cheering": 30,
                "party": 20
            }
        },
        mood_labels={
    "romantic": [
        "a romantic bride and groom moment",
        "a loving wedding couple",
        "an intimate wedding photograph",
        "a bride and groom holding each other",
        "a romantic wedding kiss"
    ],

    "happy": [
        "a joyful wedding celebration",
        "a happy bride and groom",
        "wedding guests smiling and celebrating",
        "a bride laughing at her wedding",
        "a groom happily celebrating"
    ],

    "sentimental": [
        "an emotional wedding moment",
        "a heartfelt family wedding moment",
        "a touching wedding photograph",
        "a tearful wedding ceremony",
        "an emotional wedding speech"
    ],

    "energetic": [
        "an energetic wedding reception",
        "guests dancing at a wedding",
        "a lively wedding celebration",
        "a crowded wedding dance floor",
        "an exciting wedding party"
    ],

    "calm": [
        "a calm intimate wedding moment",
        "a peaceful wedding portrait",
        "a quiet wedding ceremony",
        "a relaxed bride and groom",
        "a serene wedding photograph"
    ],

    "dramatic": [
        "a dramatic wedding photograph",
        "a cinematic bride and groom portrait",
        "a wedding photo with dramatic lighting",
        "an intense emotional wedding moment",
        "a bold artistic wedding portrait"
    ],

    "nostalgic": [
        "a timeless wedding memory",
        "a nostalgic wedding photograph",
        "a classic bride and groom portrait",
        "a traditional family wedding moment",
        "a wedding photo that feels like a memory"
    ],

    "funny": [
        "a funny wedding reaction",
        "a humorous wedding candid",
        "a silly wedding party photograph",
        "wedding guests laughing together",
        "a playful bride and groom"
    ],

    "general": [
        "a general wedding photograph",
        "a normal wedding event photo",
        "people attending a wedding",
        "a standard wedding celebration photo"
    ]
},

mood_keywords={
    "romantic": {
        "kiss": 35,
        "kissing": 35,
        "first kiss": 50,
        "holding hands": 35,
        "hand in hand": 35,
        "first dance": 45,
        "slow dancing": 35,
        "embracing": 30,
        "bride and groom": 40,
        "newlyweds": 40,
        "romantic": 40,
        "intimate": 30,
        "loving": 30,
        "couple": 25
    },

    "professional": {
        "professional portrait": 45,
        "formal portrait": 40,
        "wedding portrait": 40,
        "bride portrait": 40,
        "groom portrait": 40,
        "couple portrait": 40,
        "family portrait": 35,
        "group portrait": 30,
        "posed": 25,
        "looking at the camera": 25
    },

    "friends": {
        "friends": 35,
        "wedding party": 45,
        "bridesmaids": 40,
        "groomsmen": 40,
        "group of friends": 40,
        "guests": 20,
        "group photo": 25
    },

    "family": {
        "family": 35,
        "parents": 30,
        "mother": 20,
        "father": 20,
        "grandparents": 30,
        "family portrait": 45,
        "father daughter": 40,
        "mother son": 40
    },

    "ceremony": {
        "ceremony": 40,
        "wedding ceremony": 50,
        "altar": 35,
        "aisle": 30,
        "officiant": 30,
        "vows": 45,
        "exchanging vows": 50,
        "ring exchange": 50
    },

    "reception": {
        "reception": 45,
        "wedding reception": 50,
        "toast": 30,
        "speech": 30,
        "cake cutting": 40,
        "champagne": 25,
        "banquet": 25,
        "celebration": 25
    },

    "dancing": {
        "dance": 25,
        "dancing": 35,
        "first dance": 50,
        "slow dancing": 40,
        "dance floor": 45,
        "guests dancing": 40,
        "couple dancing": 40
    },

    "food_decor": {
        "wedding cake": 40,
        "cake": 25,
        "flowers": 25,
        "bouquet": 30,
        "centerpiece": 30,
        "candles": 25,
        "decorations": 30,
        "table setting": 25
    },

    "venue_detail": {
        "wedding venue": 45,
        "venue": 35,
        "reception hall": 40,
        "ballroom": 35,
        "chapel": 30,
        "church": 30,
        "decorated room": 30,
        "garden": 25
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "laughing": 30,
        "joyful": 40,
        "celebrating": 30,
        "cheering": 30,
        "excited": 25
    },

    "sentimental": {
        "sentimental": 40,
        "emotional": 40,
        "heartfelt": 40,
        "touching": 35,
        "tearful": 30,
        "happy tears": 40,
        "special moment": 30
    },

    "energetic": {
        "energetic": 40,
        "party": 25,
        "dancing": 35,
        "cheering": 30,
        "crowd": 20,
        "lively": 40,
        "exciting": 30
    },

    "calm": {
        "calm": 40,
        "peaceful": 40,
        "quiet": 30,
        "relaxed": 30,
        "gentle": 25,
        "serene": 40,
        "soft light": 25
    },

    "dramatic": {
        "dramatic": 45,
        "cinematic": 40,
        "spotlight": 35,
        "silhouette": 35,
        "high contrast": 30,
        "moody": 35,
        "artistic": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "timeless": 40,
        "classic": 35,
        "traditional": 30,
        "memory": 35,
        "black and white": 25
    },

    "funny": {
        "funny": 45,
        "silly": 40,
        "goofy": 40,
        "humorous": 40,
        "playful": 30,
        "laughing": 25,
        "making faces": 35
    },

    "general": {
        "wedding": 15,
        "event": 10,
        "guest": 10,
        "people": 10,
        "group": 10
    }
}
    ),

    "concert": EventProfile(
        event_type="concert",

        detail_labels={
            "performer": [
                "a singer performing on stage",
                "a musician performing live",
                "a concert performer"
            ],

            "band": [
                "a band performing live",
                "musicians playing together",
                "a live music group"
            ],

            "instruments": [
                "a musician playing guitar",
                "a musician playing drums",
                "a musician playing a musical instrument"
            ],

            "crowd": [
                "a concert crowd",
                "an audience watching live music",
                "fans cheering at a concert"
            ],

            "stage": [
                "a concert stage",
                "a brightly lit music stage",
                "a performer under stage lights"
            ],

            "festival": [
                "an outdoor music festival",
                "a large festival crowd",
                "a live festival performance"
            ]
        },

        detail_keywords={
            "performer": {
                "singer": 35,
                "performer": 35,
                "microphone": 25
            },

            "band": {
                "band": 45,
                "musicians": 35
            },

            "instruments": {
                "guitar": 35,
                "drums": 35,
                "instrument": 25
            },

            "crowd": {
                "crowd": 35,
                "audience": 35,
                "fans": 30
            },

            "stage": {
                "stage": 35,
                "stage lights": 40,
                "spotlight": 30
            },

            "festival": {
                "festival": 45,
                "outdoor concert": 40
            }
        },
        mood_labels={
    "romantic": [
        "a romantic moment during a concert",
        "a couple enjoying live music together",
        "an intimate live music performance"
    ],

    "happy": [
        "a joyful concert crowd",
        "a happy musician performing",
        "fans smiling at a concert",
        "a performer enjoying the performance",
        "a cheerful live music event"
    ],

    "sentimental": [
        "an emotional live music performance",
        "a heartfelt concert moment",
        "a touching musician performance",
        "an emotional audience reaction"
    ],

    "energetic": [
        "an energetic live concert",
        "a high energy musician performing",
        "an excited concert crowd",
        "fans dancing to live music",
        "a lively music festival"
    ],

    "calm": [
        "a calm acoustic performance",
        "a quiet intimate concert",
        "a peaceful musician portrait",
        "a relaxed audience listening to music"
    ],

    "dramatic": [
        "a dramatic live music performance",
        "a performer under dramatic stage lights",
        "a cinematic concert photograph",
        "an intense musician performance",
        "a concert with bold lighting"
    ],

    "nostalgic": [
        "a nostalgic live music photograph",
        "a timeless concert moment",
        "a classic musician performance",
        "a concert photo that feels like a memory"
    ],

    "funny": [
        "a funny performer reaction",
        "musicians joking on stage",
        "a humorous concert candid",
        "fans laughing at a concert",
        "a playful musician performance"
    ],

    "general": [
        "a general concert photograph",
        "a normal live music event",
        "people attending a concert",
        "a standard stage performance photo"
    ]
},

mood_keywords={
    "romantic": {
        "couple": 25,
        "holding hands": 30,
        "romantic": 40,
        "intimate": 30,
        "slow song": 30
    },

    "professional": {
        "performer portrait": 40,
        "musician portrait": 40,
        "professional performance": 40,
        "posed": 20,
        "stage portrait": 35,
        "band photo": 35
    },

    "friends": {
        "friends": 35,
        "group of friends": 40,
        "fans": 25,
        "band members": 35,
        "musicians": 30,
        "crowd": 20
    },

    "dancing": {
        "dance": 25,
        "dancing": 35,
        "fans dancing": 40,
        "crowd dancing": 40,
        "dance music": 30
    },

    "venue_detail": {
        "concert venue": 45,
        "stage": 35,
        "stage lights": 40,
        "festival": 35,
        "arena": 35,
        "theater": 30,
        "auditorium": 30
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "enjoying": 25,
        "joyful": 40,
        "cheering": 35,
        "applause": 30
    },

    "sentimental": {
        "emotional": 40,
        "heartfelt": 40,
        "touching": 35,
        "meaningful": 30,
        "tribute": 40,
        "dedication": 35
    },

    "energetic": {
        "energetic": 45,
        "high energy": 50,
        "cheering": 35,
        "crowd": 25,
        "lively": 40,
        "exciting": 35,
        "festival": 25
    },

    "calm": {
        "calm": 40,
        "acoustic": 35,
        "quiet": 30,
        "peaceful": 35,
        "relaxed": 30,
        "intimate performance": 40
    },

    "dramatic": {
        "dramatic": 45,
        "cinematic": 40,
        "stage lights": 40,
        "spotlight": 40,
        "silhouette": 35,
        "smoke": 25,
        "high contrast": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "classic": 35,
        "timeless": 40,
        "retro": 35,
        "vintage": 35,
        "memory": 30
    },

    "funny": {
        "funny": 45,
        "joking": 35,
        "laughing": 25,
        "playful": 30,
        "silly": 40,
        "funny reaction": 45
    },

    "general": {
        "concert": 20,
        "music": 15,
        "performer": 15,
        "stage": 10,
        "audience": 10
    }
}
    ),

    "sports": EventProfile(
        event_type="sports",

        detail_labels={
            "gameplay": [
                "athletes playing a competitive sport",
                "players competing during a game",
                "live sports action"
            ],

            "athlete": [
                "an athlete competing",
                "an individual sports player",
                "an athlete in uniform"
            ],

            "team": [
                "a sports team group photo",
                "players posing as a team",
                "teammates celebrating together"
            ],

            "fans": [
                "fans watching a sporting event",
                "a cheering sports crowd",
                "spectators in a stadium"
            ],

            "celebration": [
                "athletes celebrating a victory",
                "a team celebrating after a game",
                "a sports victory celebration"
            ],

            "award": [
                "an athlete receiving a trophy",
                "a sports medal ceremony",
                "a team holding a championship trophy"
            ]
        },

        detail_keywords={
            "gameplay": {
                "game": 25,
                "playing": 20,
                "competing": 30
            },

            "athlete": {
                "athlete": 40,
                "player": 30,
                "uniform": 20
            },

            "team": {
                "team": 40,
                "teammates": 40,
                "team photo": 45
            },

            "fans": {
                "fans": 40,
                "crowd": 30,
                "stadium": 30
            },

            "celebration": {
                "victory": 45,
                "celebrating": 30,
                "winning": 35
            },

            "award": {
                "trophy": 50,
                "medal": 45,
                "award": 35
            }
        },
        mood_labels={
    "romantic": [
        "a couple enjoying a sporting event",
        "a loving couple celebrating at a game",
        "a romantic moment at a sports venue"
    ],

    "happy": [
        "athletes happily celebrating a victory",
        "a joyful sports team celebration",
        "happy fans cheering for their team",
        "a smiling athlete after a game",
        "a proud winning team"
    ],

    "sentimental": [
        "an emotional sports award moment",
        "an athlete celebrating with family",
        "a touching team moment",
        "an emotional athlete after competition",
        "a heartfelt sports achievement"
    ],

    "energetic": [
        "an intense high energy sports moment",
        "athletes competing with high energy",
        "an exciting live sports action photo",
        "fans energetically cheering",
        "a fast competitive sports play"
    ],

    "calm": [
        "an athlete calmly preparing for competition",
        "a quiet moment before a sports game",
        "a calm sports portrait",
        "a relaxed team before competition"
    ],

    "dramatic": [
        "a dramatic moment during a sports game",
        "an intense close competitive sports moment",
        "a dramatic winning play",
        "an athlete under stadium lights",
        "a cinematic sports photograph"
    ],

    "nostalgic": [
        "a nostalgic sports memory",
        "a timeless team photograph",
        "a classic championship moment",
        "a traditional sports team portrait"
    ],

    "funny": [
        "a funny sports reaction",
        "athletes joking with teammates",
        "a humorous moment during a game",
        "a silly team photograph",
        "fans laughing at a sports event"
    ],

    "general": [
        "a general sports photograph",
        "people attending a sporting event",
        "a normal sports competition photo",
        "athletes participating in a game"
    ]
},

mood_keywords={
    "romantic": {
        "couple": 25,
        "holding hands": 30,
        "kiss": 35,
        "romantic": 40,
        "partner": 20
    },

    "professional": {
        "athlete portrait": 45,
        "team portrait": 45,
        "team photo": 45,
        "professional athlete": 40,
        "posed": 25,
        "uniform": 20
    },

    "friends": {
        "friends": 35,
        "teammates": 45,
        "team": 35,
        "players": 25,
        "group photo": 25,
        "fans": 20
    },

    "family": {
        "family": 40,
        "parents": 30,
        "children": 25,
        "family celebration": 40,
        "family photo": 35
    },

    "ceremony": {
        "award ceremony": 45,
        "medal ceremony": 50,
        "trophy presentation": 50,
        "championship ceremony": 50,
        "podium": 30
    },

    "venue_detail": {
        "stadium": 40,
        "arena": 40,
        "field": 30,
        "court": 30,
        "track": 30,
        "sports venue": 45,
        "gymnasium": 35
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "victory": 45,
        "winning": 40,
        "celebrating": 35,
        "cheering": 35,
        "proud": 35
    },

    "sentimental": {
        "emotional": 40,
        "heartfelt": 40,
        "family moment": 35,
        "achievement": 35,
        "proud": 30,
        "retirement": 40,
        "tribute": 40
    },

    "energetic": {
        "energetic": 45,
        "high energy": 50,
        "action": 35,
        "running": 30,
        "competing": 35,
        "cheering": 35,
        "intense": 35
    },

    "calm": {
        "calm": 40,
        "preparing": 25,
        "focused": 35,
        "quiet": 30,
        "relaxed": 30,
        "waiting": 20
    },

    "dramatic": {
        "dramatic": 45,
        "intense": 40,
        "winning play": 50,
        "final seconds": 50,
        "close game": 45,
        "stadium lights": 35,
        "cinematic": 40
    },

    "nostalgic": {
        "nostalgic": 45,
        "classic": 35,
        "championship memory": 45,
        "team history": 40,
        "timeless": 40,
        "traditional": 30
    },

    "funny": {
        "funny": 45,
        "joking": 35,
        "laughing": 25,
        "silly": 40,
        "funny reaction": 45,
        "making faces": 35
    },

    "general": {
        "sports": 20,
        "game": 15,
        "athlete": 15,
        "player": 10,
        "team": 10
    }
}
    ),

    "corporate": EventProfile(
        event_type="corporate",

        detail_labels={
            "presentation": [
                "a corporate presentation",
                "a business speaker giving a presentation",
                "a professional presenting on stage"
            ],

            "meeting": [
                "a business meeting",
                "professionals seated around a conference table",
                "a corporate planning session"
            ],

            "networking": [
                "business professionals networking",
                "people talking at a corporate event",
                "professional networking at a conference"
            ],

            "conference": [
                "a professional business conference",
                "a conference audience",
                "a corporate seminar"
            ],

            "team": [
                "a corporate team group photo",
                "employees posing together",
                "an office team celebration"
            ],

            "awards": [
                "a corporate award ceremony",
                "an employee receiving an award",
                "a business achievement presentation"
            ]
        },

        detail_keywords={
            "presentation": {
                "presentation": 45,
                "presenter": 35,
                "speaker": 30
            },

            "meeting": {
                "meeting": 45,
                "conference table": 40,
                "discussion": 25
            },

            "networking": {
                "networking": 50,
                "business professionals": 35
            },

            "conference": {
                "conference": 45,
                "seminar": 40,
                "audience": 20
            },

            "team": {
                "team": 35,
                "employees": 30,
                "coworkers": 30
            },

            "awards": {
                "award": 40,
                "achievement": 35,
                "recognition": 35
            }
        },
        mood_labels={
    "romantic": [
        "a couple attending a corporate event",
        "a romantic moment at a formal business event",
        "a couple posing at a company celebration"
    ],

    "happy": [
        "happy employees celebrating together",
        "a joyful corporate team photograph",
        "business professionals smiling",
        "an employee happily receiving an award",
        "a cheerful company celebration"
    ],

    "sentimental": [
        "an emotional employee recognition moment",
        "a heartfelt company award presentation",
        "a touching retirement celebration",
        "a meaningful corporate achievement",
        "coworkers celebrating an important milestone"
    ],

    "energetic": [
        "an energetic corporate celebration",
        "an exciting business presentation",
        "a lively networking event",
        "employees enthusiastically celebrating",
        "a high energy conference"
    ],

    "calm": [
        "a calm business meeting",
        "a quiet professional presentation",
        "a relaxed networking conversation",
        "a peaceful corporate portrait",
        "professionals calmly discussing business"
    ],

    "dramatic": [
        "a dramatic corporate presentation",
        "a speaker under stage lighting",
        "a cinematic business conference photograph",
        "a bold professional portrait",
        "an intense keynote presentation"
    ],

    "nostalgic": [
        "a nostalgic company anniversary photograph",
        "a timeless corporate team portrait",
        "a classic employee group photograph",
        "a company milestone memory"
    ],

    "funny": [
        "coworkers laughing together",
        "a funny corporate event reaction",
        "employees joking at a company party",
        "a humorous office team photograph",
        "a playful business event moment"
    ],

    "general": [
        "a general corporate event photograph",
        "business professionals attending an event",
        "a normal company meeting photo",
        "a standard business conference photograph"
    ]
},

mood_keywords={
    "romantic": {
        "couple": 25,
        "partner": 20,
        "romantic": 40,
        "holding hands": 30
    },

    "professional": {
        "professional": 35,
        "business professional": 45,
        "corporate portrait": 45,
        "professional portrait": 45,
        "formal": 25,
        "business attire": 35,
        "suit": 20,
        "presentation": 25
    },

    "friends": {
        "coworkers": 40,
        "colleagues": 40,
        "team": 35,
        "employees": 30,
        "group photo": 25,
        "networking": 25
    },

    "ceremony": {
        "award ceremony": 45,
        "recognition ceremony": 50,
        "award presentation": 45,
        "employee recognition": 45,
        "retirement ceremony": 45
    },

    "reception": {
        "networking reception": 50,
        "corporate reception": 50,
        "company party": 40,
        "business dinner": 35,
        "cocktail reception": 45,
        "banquet": 30
    },

    "venue_detail": {
        "conference room": 40,
        "conference hall": 40,
        "business venue": 45,
        "office": 30,
        "stage": 25,
        "trade show": 40,
        "convention center": 40
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "celebrating": 35,
        "achievement": 35,
        "success": 35,
        "award": 25,
        "cheering": 30
    },

    "sentimental": {
        "emotional": 35,
        "heartfelt": 40,
        "recognition": 35,
        "retirement": 40,
        "milestone": 40,
        "tribute": 40,
        "meaningful": 30
    },

    "energetic": {
        "energetic": 40,
        "exciting": 35,
        "enthusiastic": 35,
        "networking": 25,
        "celebrating": 30,
        "crowd": 20,
        "applause": 30
    },

    "calm": {
        "calm": 40,
        "meeting": 25,
        "discussion": 25,
        "quiet": 30,
        "focused": 35,
        "professional": 20,
        "relaxed": 30
    },

    "dramatic": {
        "dramatic": 45,
        "keynote": 40,
        "spotlight": 35,
        "stage lighting": 35,
        "cinematic": 40,
        "bold": 30,
        "high contrast": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "anniversary": 40,
        "milestone": 40,
        "company history": 45,
        "classic": 30,
        "timeless": 40
    },

    "funny": {
        "funny": 45,
        "joking": 35,
        "laughing": 25,
        "playful": 30,
        "silly": 40,
        "funny reaction": 45
    },

    "general": {
        "corporate": 20,
        "business": 15,
        "conference": 15,
        "professional": 10,
        "meeting": 10
    }
}
    ),

    "general": EventProfile(
        event_type="general",

        detail_labels={
            "portrait": [
                "a portrait photo",
                "a person posing for a photo",
                "a professional portrait"
            ],

            "group": [
                "a group photo",
                "people posing together",
                "a social group at an event"
            ],

            "celebration": [
                "people celebrating",
                "a social party",
                "a happy event"
            ],

            "food": [
                "food served at an event",
                "a table of food",
                "an event meal"
            ],

            "venue": [
                "an event venue",
                "a decorated event room",
                "an indoor gathering space"
            ]
        },

        detail_keywords={
            "portrait": {
                "portrait": 40,
                "posing": 30
            },

            "group": {
                "group": 35,
                "people": 20
            },

            "celebration": {
                "celebrating": 35,
                "party": 30
            },

            "food": {
                "food": 35,
                "meal": 25,
                "table": 15
            },

            "venue": {
                "venue": 40,
                "room": 20,
                "decorated": 20
            }
        },
        mood_labels={
    "romantic": [
        "a couple attending a corporate event",
        "a romantic moment at a formal business event",
        "a couple posing at a company celebration"
    ],

    "happy": [
        "happy employees celebrating together",
        "a joyful corporate team photograph",
        "business professionals smiling",
        "an employee happily receiving an award",
        "a cheerful company celebration"
    ],

    "sentimental": [
        "an emotional employee recognition moment",
        "a heartfelt company award presentation",
        "a touching retirement celebration",
        "a meaningful corporate achievement",
        "coworkers celebrating an important milestone"
    ],

    "energetic": [
        "an energetic corporate celebration",
        "an exciting business presentation",
        "a lively networking event",
        "employees enthusiastically celebrating",
        "a high energy conference"
    ],

    "calm": [
        "a calm business meeting",
        "a quiet professional presentation",
        "a relaxed networking conversation",
        "a peaceful corporate portrait",
        "professionals calmly discussing business"
    ],

    "dramatic": [
        "a dramatic corporate presentation",
        "a speaker under stage lighting",
        "a cinematic business conference photograph",
        "a bold professional portrait",
        "an intense keynote presentation"
    ],

    "nostalgic": [
        "a nostalgic company anniversary photograph",
        "a timeless corporate team portrait",
        "a classic employee group photograph",
        "a company milestone memory"
    ],

    "funny": [
        "coworkers laughing together",
        "a funny corporate event reaction",
        "employees joking at a company party",
        "a humorous office team photograph",
        "a playful business event moment"
    ],

    "general": [
        "a general corporate event photograph",
        "business professionals attending an event",
        "a normal company meeting photo",
        "a standard business conference photograph"
    ]
},

mood_keywords={
    "romantic": {
        "couple": 25,
        "partner": 20,
        "romantic": 40,
        "holding hands": 30
    },

    "professional": {
        "professional": 35,
        "business professional": 45,
        "corporate portrait": 45,
        "professional portrait": 45,
        "formal": 25,
        "business attire": 35,
        "suit": 20,
        "presentation": 25
    },

    "friends": {
        "coworkers": 40,
        "colleagues": 40,
        "team": 35,
        "employees": 30,
        "group photo": 25,
        "networking": 25
    },

    "ceremony": {
        "award ceremony": 45,
        "recognition ceremony": 50,
        "award presentation": 45,
        "employee recognition": 45,
        "retirement ceremony": 45
    },

    "reception": {
        "networking reception": 50,
        "corporate reception": 50,
        "company party": 40,
        "business dinner": 35,
        "cocktail reception": 45,
        "banquet": 30
    },

    "venue_detail": {
        "conference room": 40,
        "conference hall": 40,
        "business venue": 45,
        "office": 30,
        "stage": 25,
        "trade show": 40,
        "convention center": 40
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "celebrating": 35,
        "achievement": 35,
        "success": 35,
        "award": 25,
        "cheering": 30
    },

    "sentimental": {
        "emotional": 35,
        "heartfelt": 40,
        "recognition": 35,
        "retirement": 40,
        "milestone": 40,
        "tribute": 40,
        "meaningful": 30
    },

    "energetic": {
        "energetic": 40,
        "exciting": 35,
        "enthusiastic": 35,
        "networking": 25,
        "celebrating": 30,
        "crowd": 20,
        "applause": 30
    },

    "calm": {
        "calm": 40,
        "meeting": 25,
        "discussion": 25,
        "quiet": 30,
        "focused": 35,
        "professional": 20,
        "relaxed": 30
    },

    "dramatic": {
        "dramatic": 45,
        "keynote": 40,
        "spotlight": 35,
        "stage lighting": 35,
        "cinematic": 40,
        "bold": 30,
        "high contrast": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "anniversary": 40,
        "milestone": 40,
        "company history": 45,
        "classic": 30,
        "timeless": 40
    },

    "funny": {
        "funny": 45,
        "joking": 35,
        "laughing": 25,
        "playful": 30,
        "silly": 40,
        "funny reaction": 45
    },

    "general": {
        "corporate": 20,
        "business": 15,
        "conference": 15,
        "professional": 10,
        "meeting": 10
    }
}
    ),

    "unknown": EventProfile(
        event_type="unknown",

        detail_labels={
            "unclear": [
                "an unclear event photo",
                "a photo with no recognizable event",
                "an image that is difficult to classify"
            ],

            "random": [
                "a random everyday photo",
                "an unrelated image",
                "a photo with no event context"
            ]
        },

        detail_keywords={
            "unclear": {
                "unclear": 50,
                "unknown": 50
            },

            "random": {
                "random": 50,
                "unrelated": 50
            }
        },
        mood_labels={
    "romantic": [
        "a possible romantic moment",
        "two people showing affection",
        "a possible couple photograph"
    ],

    "happy": [
        "people appearing happy",
        "a person smiling",
        "a joyful-looking photograph"
    ],

    "sentimental": [
        "an emotional-looking photograph",
        "a meaningful personal moment",
        "a possible sentimental memory"
    ],

    "energetic": [
        "an active energetic photograph",
        "people moving with high energy",
        "an exciting-looking image"
    ],

    "calm": [
        "a calm peaceful photograph",
        "a quiet relaxed image",
        "a serene-looking photograph"
    ],

    "dramatic": [
        "a dramatic-looking photograph",
        "an image with intense lighting",
        "a cinematic-looking image"
    ],

    "nostalgic": [
        "a nostalgic-looking photograph",
        "an image that feels like an old memory",
        "a timeless-looking photograph"
    ],

    "funny": [
        "a funny-looking photograph",
        "a person making a humorous expression",
        "a silly candid image"
    ],

    "general": [
        "a general unclassified photograph",
        "a photograph with no clear mood",
        "an image with an unknown context",
        "a normal everyday photograph"
    ]
},

mood_keywords={
    "romantic": {
        "couple": 25,
        "kiss": 35,
        "holding hands": 30,
        "romantic": 40,
        "loving": 30
    },

    "professional": {
        "portrait": 25,
        "professional": 35,
        "formal": 25,
        "posed": 25
    },

    "friends": {
        "friends": 40,
        "group of friends": 45,
        "group": 15
    },

    "family": {
        "family": 40,
        "parents": 30,
        "children": 25,
        "family portrait": 40
    },

    "dancing": {
        "dance": 25,
        "dancing": 35,
        "dance floor": 40
    },

    "food_decor": {
        "food": 25,
        "cake": 25,
        "decorations": 30,
        "flowers": 25
    },

    "venue_detail": {
        "venue": 40,
        "room": 20,
        "building": 20,
        "hall": 25
    },

    "happy": {
        "happy": 35,
        "smiling": 25,
        "laughing": 30,
        "joyful": 40
    },

    "sentimental": {
        "emotional": 40,
        "heartfelt": 40,
        "touching": 35,
        "meaningful": 30
    },

    "energetic": {
        "energetic": 40,
        "active": 25,
        "exciting": 35,
        "moving": 20
    },

    "calm": {
        "calm": 40,
        "peaceful": 40,
        "quiet": 30,
        "relaxed": 30
    },

    "dramatic": {
        "dramatic": 45,
        "cinematic": 40,
        "spotlight": 35,
        "high contrast": 30
    },

    "nostalgic": {
        "nostalgic": 45,
        "memory": 35,
        "classic": 35,
        "timeless": 40
    },

    "funny": {
        "funny": 45,
        "silly": 40,
        "goofy": 40,
        "laughing": 25
    },

    "general": {
        "photo": 5,
        "image": 5,
        "person": 10,
        "people": 10,
        "group": 10
    }
}
    )
    }
class MediaMappingConfig:
    UNIVERSAL_EVENT_MOMENT_KEYWORDS: dict[str, dict[str, int]] = {
        "energetic": {
            "firework": 100,
            "fireworks": 100,
            "pyrotechnic": 95,
            "pyrotechnics": 95,
            "sparkler": 85,
            "sparklers": 85,
        },
        "happy": {
            "firework": 90,
            "fireworks": 90,
            "pyrotechnic": 85,
            "pyrotechnics": 85,
            "sparkler": 80,
            "sparklers": 80,
        },
        "dramatic": {
            "firework": 90,
            "fireworks": 90,
            "pyrotechnic": 90,
            "pyrotechnics": 90,
            "sparkler": 75,
            "sparklers": 75,
        },
        "general": {
            "firework": 90,
            "fireworks": 90,
            "pyrotechnic": 85,
            "pyrotechnics": 85,
            "sparkler": 75,
            "sparklers": 75,
        },
    }

    THEME_CATEGORY_MAP: dict[str, tuple[str, ...]] = {
        "romance": ("romantic", "sentimental", "calm"),
        "friendship": ("friends", "happy", "funny"),
        "family": ("family", "sentimental", "happy", "nostalgic"),
        "celebration": ("happy", "energetic", "dancing", "reception"),
        "professional": ("professional", "ceremony", "venue_detail"),
        "funny": ("funny", "happy", "friends"),
        "emotional": ("sentimental", "nostalgic", "romantic", "dramatic"),
        "general": ("general"),
        "unknown": ("general"),
    }

    EVENT_CATEGORY_MAP: dict[str, tuple[str, ...]] = {
        "wedding": (
            "ceremony",
            "reception",
            "romantic",
            "family",
            "friends",
            "dancing",
            "food_decor",
            "venue_detail",
        ),
        "birthday": ("happy", "family", "friends", "funny", "food_decor"),
        "graduation": ("professional", "family", "friends", "happy"),
        "concert": ("energetic", "dramatic", "friends", "general"),
        "sports": ("energetic", "dramatic", "friends", "happy"),
        "corporate": ("professional", "friends", "venue_detail", "general"),
        "general": ("general"),
        "unknown": ("general"),
    }

    MUSIC_MOOD_MAP: dict[str, tuple[str, ...]] = {
        "romantic": ("romantic", "sentimental", "calm"),
        "upbeat": ("energetic", "happy", "upbeat"),
        "calm": ("calm", "sentimental", "romantic"),
        "dramatic": ("dramatic", "energetic"),
        "fun": ("fun", "funny", "happy", "energetic"),
        "unknown": (),
        "none": (),
    }

    TIMING_SETTINGS: dict[str, dict[str, float]] = {
        "slow": {"photo_seconds": 7.0, "video_clip_seconds": 30.0},
        "medium": {"photo_seconds": 5.0, "video_clip_seconds": 22.0},
        "fast": {"photo_seconds": 3.5, "video_clip_seconds": 15.0},
        "unknown": {"photo_seconds": 5.0, "video_clip_seconds": 22.0},
    }
