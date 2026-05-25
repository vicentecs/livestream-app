import asyncio

from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, URLSafeSerializer

import storage
from config import settings
from models import User

_serializer = URLSafeSerializer(settings.app_secret_key, salt="session")
SESSION_COOKIE = "session"


class StreamLock:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner: str | None = None

    @property
    def locked(self) -> bool:
        return self._owner is not None

    @property
    def owner(self) -> str | None:
        return self._owner

    async def acquire(self, email: str) -> bool:
        async with self._lock:
            if self._owner is not None and self._owner != email:
                return False
            self._owner = email
            return True

    async def release(self, email: str) -> None:
        async with self._lock:
            if self._owner == email:
                self._owner = None

    async def force_release(self) -> None:
        async with self._lock:
            self._owner = None


stream_lock = StreamLock()


def make_session_cookie(email: str) -> str:
    return _serializer.dumps({"email": email})


def read_session_cookie(token: str) -> str | None:
    try:
        data = _serializer.loads(token)
        return data.get("email")
    except BadSignature:
        return None


async def get_current_user(request: Request) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "auth_required", "message": "Sessão não encontrada."},
        )
    email = read_session_cookie(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "auth_required", "message": "Sessão inválida."},
        )
    user = await storage.get_user(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "auth_required", "message": "Usuário não encontrado."},
        )
    return user


async def get_optional_user(request: Request) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    email = read_session_cookie(token)
    if not email:
        return None
    return await storage.get_user(email)
