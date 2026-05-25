import asyncio
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import auth
from config import settings
from models import BroadcastState, LiveStartRequest, User


class YouTubeError(RuntimeError):
    def __init__(self, status: int, message: str, detail: str | None = None):
        self.status = status
        self.message = message
        self.detail = detail
        super().__init__(f"{status}: {message}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_title() -> str:
    prefix = settings.channel_prefix.strip()
    court = settings.court_number.strip()
    date = datetime.now().strftime("%d-%m-%Y")
    parts = [p for p in (prefix, date, f"Quadra {court}" if court else "") if p]
    return " - ".join(parts) if parts else f"Live {datetime.now().strftime('%Y-%m-%d %H:%M')}"


async def _build_service(user: User):
    creds = await auth.ensure_valid_token(user)
    return await asyncio.to_thread(
        build, "youtube", "v3", credentials=creds, cache_discovery=False
    )


def _raise_from_http(e: HttpError) -> None:
    status = e.resp.status if e.resp else 502
    msg = e._get_reason() if hasattr(e, "_get_reason") else str(e)
    raise YouTubeError(status, "YouTube API falhou", msg)


async def create_broadcast(user: User, req: LiveStartRequest) -> BroadcastState:
    yt = await _build_service(user)
    title = req.title or _default_title()

    def _insert_broadcast() -> dict:
        try:
            return yt.liveBroadcasts().insert(
                part="snippet,status,contentDetails",
                body={
                    "snippet": {
                        "title": title,
                        "description": req.description or "",
                        "scheduledStartTime": _now_iso(),
                    },
                    "status": {
                        "privacyStatus": req.privacy,
                        "selfDeclaredMadeForKids": False,
                    },
                    "contentDetails": {
                        "enableAutoStart": False,
                        "enableAutoStop": False,
                        "monitorStream": {"enableMonitorStream": False},
                    },
                },
            ).execute()
        except HttpError as e:
            _raise_from_http(e)

    def _insert_stream() -> dict:
        try:
            return yt.liveStreams().insert(
                part="snippet,cdn,contentDetails",
                body={
                    "snippet": {"title": f"{title} stream"},
                    "cdn": {
                        "frameRate": "variable",
                        "ingestionType": "rtmp",
                        "resolution": "variable",
                    },
                    "contentDetails": {"isReusable": False},
                },
            ).execute()
        except HttpError as e:
            _raise_from_http(e)

    def _bind(broadcast_id: str, stream_id: str) -> dict:
        try:
            return yt.liveBroadcasts().bind(
                id=broadcast_id,
                part="id,contentDetails",
                streamId=stream_id,
            ).execute()
        except HttpError as e:
            _raise_from_http(e)

    broadcast = await asyncio.to_thread(_insert_broadcast)
    stream = await asyncio.to_thread(_insert_stream)
    await asyncio.to_thread(_bind, broadcast["id"], stream["id"])

    stream_key = stream["cdn"]["ingestionInfo"]["streamName"]
    return BroadcastState(
        broadcast_id=broadcast["id"],
        stream_id=stream["id"],
        stream_key=stream_key,
        youtube_url=f"https://youtu.be/{broadcast['id']}",
        started_at=datetime.now(timezone.utc),
    )


async def transition(user: User, broadcast_id: str, status: str) -> None:
    yt = await _build_service(user)

    def _do() -> dict:
        try:
            return yt.liveBroadcasts().transition(
                broadcastStatus=status,
                id=broadcast_id,
                part="id,status",
            ).execute()
        except HttpError as e:
            _raise_from_http(e)

    await asyncio.to_thread(_do)


async def stream_status(user: User, stream_id: str) -> str:
    yt = await _build_service(user)

    def _do() -> dict:
        try:
            return yt.liveStreams().list(part="status", id=stream_id).execute()
        except HttpError as e:
            _raise_from_http(e)

    resp = await asyncio.to_thread(_do)
    items = resp.get("items", [])
    if not items:
        return "noStream"
    return items[0]["status"]["streamStatus"]


async def wait_active(user: User, stream_id: str, timeout: float = 60.0, interval: float = 3.0) -> bool:
    elapsed = 0.0
    while elapsed < timeout:
        status = await stream_status(user, stream_id)
        if status == "active":
            return True
        await asyncio.sleep(interval)
        elapsed += interval
    return False


async def end_broadcast(user: User, broadcast_id: str) -> None:
    await transition(user, broadcast_id, "complete")
