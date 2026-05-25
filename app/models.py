from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class OAuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_uri: str = "https://oauth2.googleapis.com/token"
    expiry: datetime
    scopes: list[str] = Field(default_factory=list)


class BroadcastState(BaseModel):
    broadcast_id: str
    stream_id: str
    stream_key: str
    youtube_url: HttpUrl
    started_at: datetime


class User(BaseModel):
    email: str
    name: str
    picture: str | None = None
    tokens: OAuthTokens
    broadcast: BroadcastState | None = None


class UsersFile(BaseModel):
    users: dict[str, User] = Field(default_factory=dict)


Privacy = Literal["public", "unlisted", "private"]


class LiveStartRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    privacy: Privacy = "public"


class LiveStartResponse(BaseModel):
    status: Literal["started"] = "started"
    broadcast_id: str
    youtube_url: HttpUrl


class LiveStopResponse(BaseModel):
    status: Literal["stopped"] = "stopped"
    broadcast_id: str


class UserSummary(BaseModel):
    email: str
    name: str


class BroadcastSummary(BaseModel):
    broadcast_id: str
    stream_id: str
    youtube_url: HttpUrl
    started_at: datetime
    uptime_seconds: int


class StatusResponse(BaseModel):
    stream_locked: bool
    active_user: str | None
    current_user: UserSummary | None
    broadcast: BroadcastSummary | None


class ConfigResponse(BaseModel):
    rtsp_url_masked: str
    pipeline_mode: Literal["remux"] = "remux"
    video_codec: str = "h264"
    audio_codec: str = "aac"
    container_output: str = "flv"
    default_title: str


class HealthResponse(BaseModel):
    app: Literal["ok"] = "ok"
    restreamer: Literal["ok", "unreachable"]
    restreamer_ffmpeg: Literal["idle", "running", "unknown"] = "unknown"


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: str | None = None
    active_user: str | None = None
