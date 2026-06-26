from dataclasses import dataclass

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

@dataclass
class uploadVidFrames:
    video_id: int
    event_id: int
    frame_num: int
    frame_time_sec: int
