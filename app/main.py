import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

import auth
import restreamer
import storage
import youtube
from config import settings
from middleware import (
    SESSION_COOKIE,
    get_current_user,
    get_optional_user,
    make_session_cookie,
    stream_lock,
)
from models import (
    BroadcastSummary,
    ConfigResponse,
    HealthResponse,
    LiveStartRequest,
    LiveStartResponse,
    LiveStopResponse,
    StatusResponse,
    User,
    UserSummary,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("livestream")

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("Starting livestream-orchestrator")
    yield
    log.info("Shutting down")


app = FastAPI(title="Livestream Orchestrator", version="0.1.0", lifespan=lifespan)


# ----------- páginas estáticas -----------

@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# ----------- auth -----------

@app.get("/auth/login")
async def auth_login() -> RedirectResponse:
    url, _state = auth.build_authorization_url()
    return RedirectResponse(url, status_code=302)


@app.get("/auth/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code or not state:
        return RedirectResponse("/?error=auth_failed", status_code=302)
    try:
        user = await auth.exchange_code_for_user(code, state)
    except Exception:
        log.exception("OAuth callback falhou")
        return RedirectResponse("/?error=auth_failed", status_code=302)

    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(
        SESSION_COOKIE,
        make_session_cookie(user.email),
        httponly=True,
        samesite="lax",
        secure=settings.app_public_url.startswith("https://"),
        max_age=60 * 60 * 24 * 30,
    )
    return resp


@app.post("/auth/logout")
async def auth_logout() -> RedirectResponse:
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# ----------- status -----------

@app.get("/status", response_model=StatusResponse)
async def get_status(user: User | None = Depends(get_optional_user)) -> StatusResponse:
    broadcast = None
    if stream_lock.locked and user and stream_lock.owner == user.email and user.broadcast:
        elapsed = int((datetime.now(timezone.utc) - user.broadcast.started_at).total_seconds())
        broadcast = BroadcastSummary(
            broadcast_id=user.broadcast.broadcast_id,
            stream_id=user.broadcast.stream_id,
            youtube_url=user.broadcast.youtube_url,
            started_at=user.broadcast.started_at,
            uptime_seconds=max(elapsed, 0),
        )
    return StatusResponse(
        stream_locked=stream_lock.locked,
        active_user=stream_lock.owner,
        current_user=UserSummary(email=user.email, name=user.name) if user else None,
        broadcast=broadcast,
    )


# ----------- live -----------

@app.post("/live/start", response_model=LiveStartResponse)
async def live_start(
    body: LiveStartRequest | None = None,
    user: User = Depends(get_current_user),
) -> LiveStartResponse:
    req = body or LiveStartRequest()

    acquired = await stream_lock.acquire(user.email)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "stream_busy",
                "message": "O stream está em uso por outro usuário.",
                "active_user": stream_lock.owner,
            },
        )

    try:
        broadcast = await youtube.create_broadcast(user, req)
        await restreamer.start(broadcast.stream_key)

        active = await youtube.wait_active(user, broadcast.stream_id, timeout=60.0, interval=3.0)
        if not active:
            raise youtube.YouTubeError(504, "Stream não ficou ativo dentro do tempo limite")

        await youtube.transition(user, broadcast.broadcast_id, "live")
        await storage.set_broadcast(user.email, broadcast)
        log.info("Live iniciada: user=%s broadcast=%s", user.email, broadcast.broadcast_id)
        return LiveStartResponse(broadcast_id=broadcast.broadcast_id, youtube_url=broadcast.youtube_url)

    except youtube.YouTubeError as e:
        await _cleanup_failed(user.email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "upstream_error", "message": e.message, "detail": e.detail},
        )
    except restreamer.RestreamerError as e:
        await _cleanup_failed(user.email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "upstream_error", "message": e.message, "detail": e.detail},
        )
    except Exception:
        log.exception("Falha inesperada em /live/start")
        await _cleanup_failed(user.email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "internal_error", "message": "Erro interno ao iniciar live."},
        )


async def _cleanup_failed(email: str) -> None:
    try:
        await restreamer.stop()
    except Exception:
        log.exception("Cleanup restreamer falhou")
    await stream_lock.release(email)


@app.post("/live/stop", response_model=LiveStopResponse)
async def live_stop(user: User = Depends(get_current_user)) -> LiveStopResponse:
    if not stream_lock.locked or stream_lock.owner != user.email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "no_active_broadcast", "message": "Nenhuma live em andamento para este usuário."},
        )
    if user.broadcast is None:
        await stream_lock.release(user.email)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "no_active_broadcast", "message": "Estado inconsistente — lock liberado."},
        )

    broadcast_id = user.broadcast.broadcast_id
    try:
        await restreamer.stop()
    except Exception:
        log.exception("Erro ao parar restreamer")

    try:
        await youtube.end_broadcast(user, broadcast_id)
    except Exception:
        log.exception("Erro ao encerrar broadcast no YouTube")

    await storage.clear_broadcast(user.email)
    await stream_lock.release(user.email)
    log.info("Live encerrada: user=%s broadcast=%s", user.email, broadcast_id)
    return LiveStopResponse(broadcast_id=broadcast_id)


# ----------- config -----------

@app.get("/config", response_model=ConfigResponse)
async def get_config(_: User = Depends(get_current_user)) -> ConfigResponse:
    return ConfigResponse(
        rtsp_url_masked=_mask_rtsp(settings.rtsp_url),
        default_title=youtube._default_title(),
    )


def _mask_rtsp(url: str) -> str:
    return re.sub(r"://([^:]+):([^@]+)@", "://***:***@", url)


# ----------- health -----------

@app.get("/health", response_model=HealthResponse)
async def health() -> JSONResponse:
    restreamer_ok = False
    ffmpeg_state = "unknown"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.restreamer_url}/api")
            if r.status_code < 500:
                restreamer_ok = True
    except httpx.HTTPError:
        pass

    if restreamer_ok:
        try:
            state = await restreamer.process_state()
            ffmpeg_state = "running" if state == "running" else ("idle" if state in ("idle", "finished") else "unknown")
        except Exception:
            ffmpeg_state = "unknown"

    body = HealthResponse(
        restreamer="ok" if restreamer_ok else "unreachable",
        restreamer_ffmpeg=ffmpeg_state,
    ).model_dump()
    return JSONResponse(content=body, status_code=200 if restreamer_ok else 503)
