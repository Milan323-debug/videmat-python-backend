from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum

class DownloadType(str, Enum):
    video = "video"
    audio = "audio"

class JobStatus(str, Enum):
    pending = "pending"
    downloading = "downloading"
    done = "done"
    error = "error"

# ── Request Models ───────────────────────────────────────
class VideoInfoRequest(BaseModel):
    url: str

class DownloadStartRequest(BaseModel):
    url: str
    format_id: str
    ext: str
    quality: str
    title: str
    video_id: str
    thumbnail: Optional[str] = ""
    uploader: Optional[str] = ""
    duration: Optional[int] = 0
    filesize: Optional[int] = 0
    type: Optional[str] = "video"

# ── Response Models ──────────────────────────────────────
class DownloadOption(BaseModel):
    id: str
    label: str
    type: str
    quality: str
    format: str
    ext: str
    filesize: Optional[int] = None
    icon: str

class VideoInfo(BaseModel):
    id: str
    title: str
    thumbnail: str
    duration: int
    uploader: str
    view_count: int
    description: str
    options: List[DownloadOption]

class JobStatusResponse(BaseModel):
    id: str
    status: JobStatus
    progress: float
    error: Optional[str] = None

# ── MongoDB Document Models ──────────────────────────────
class HistoryDocument(BaseModel):
    job_id: str
    url: str
    video_id: str
    title: str
    thumbnail: Optional[str] = ""
    uploader: Optional[str] = ""
    duration: Optional[int] = 0
    quality: str
    ext: str
    filesize: Optional[int] = 0
    type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class VideoCacheDocument(BaseModel):
    url: str
    video_id: str
    data: Any
    cached_at: datetime = Field(default_factory=datetime.utcnow)
