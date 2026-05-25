import httpx

from config import settings

PROCESS_ID = "livestream-orchestrator"
YOUTUBE_RTMP = "rtmp://a.rtmp.youtube.com/live2"


class RestreamerError(RuntimeError):
    def __init__(self, status: int, message: str, detail: str | None = None):
        self.status = status
        self.message = message
        self.detail = detail
        super().__init__(f"{status}: {message}")


_token: str | None = None


async def _login(client: httpx.AsyncClient) -> str:
    global _token
    if _token:
        return _token
    r = await client.post(
        f"{settings.restreamer_url}/api/login",
        json={"username": settings.restreamer_user, "password": settings.restreamer_pass},
    )
    if r.status_code != 200:
        raise RestreamerError(r.status_code, "Login no Restreamer falhou", r.text[:200])
    _token = r.json().get("access_token")
    if not _token:
        raise RestreamerError(500, "Restreamer não retornou access_token")
    return _token


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    async with httpx.AsyncClient(timeout=15.0) as client:
        token = await _login(client)
        headers = kwargs.pop("headers", {}) | {"Authorization": f"Bearer {token}"}
        r = await client.request(method, f"{settings.restreamer_url}{path}", headers=headers, **kwargs)
        if r.status_code == 401:
            global _token
            _token = None
            token = await _login(client)
            headers["Authorization"] = f"Bearer {token}"
            r = await client.request(method, f"{settings.restreamer_url}{path}", headers=headers, **kwargs)
        return r


def _process_config(stream_key: str) -> dict:
    output_url = f"{YOUTUBE_RTMP}/{stream_key}"
    return {
        "id": PROCESS_ID,
        "type": "ffmpeg",
        "reference": "livestream",
        "input": [
            {
                "id": "input_0",
                "address": settings.rtsp_url,
                "options": ["-rtsp_transport", "tcp", "-fflags", "+genpts"],
            }
        ],
        "output": [
            {
                "id": "output_0",
                "address": output_url,
                "options": [
                    "-c:v", "copy",
                    "-c:a", "copy",
                    "-f", "flv",
                ],
            }
        ],
        "options": ["-loglevel", "info"],
        "reconnect": True,
        "reconnect_delay_seconds": 5,
        "autostart": True,
        "stale_timeout_seconds": 30,
    }


async def _delete_if_exists() -> None:
    r = await _request("DELETE", f"/api/v3/process/{PROCESS_ID}")
    if r.status_code not in (200, 204, 404):
        raise RestreamerError(r.status_code, "Falha ao remover processo anterior", r.text[:200])


async def start(stream_key: str) -> None:
    await _delete_if_exists()
    cfg = _process_config(stream_key)
    r = await _request("POST", "/api/v3/process", json=cfg)
    if r.status_code not in (200, 201):
        raise RestreamerError(r.status_code, "Falha ao criar processo FFmpeg", r.text[:300])


async def stop() -> None:
    r = await _request("PUT", f"/api/v3/process/{PROCESS_ID}/command", json={"command": "stop"})
    if r.status_code not in (200, 204, 404):
        raise RestreamerError(r.status_code, "Falha ao parar processo FFmpeg", r.text[:200])
    await _delete_if_exists()


async def process_state() -> str:
    r = await _request("GET", f"/api/v3/process/{PROCESS_ID}/state")
    if r.status_code == 404:
        return "idle"
    if r.status_code != 200:
        return "unknown"
    data = r.json()
    return data.get("exec", "unknown")
