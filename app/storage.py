import asyncio
import json
from pathlib import Path

from models import OAuthTokens, User, UsersFile

DATA_DIR = Path(__file__).parent / "data"
USERS_FILE = DATA_DIR / "users.json"

_lock = asyncio.Lock()


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


async def _load_unlocked() -> UsersFile:
    _ensure_dir()
    if not USERS_FILE.exists():
        return UsersFile()
    raw = await asyncio.to_thread(USERS_FILE.read_text, encoding="utf-8")
    if not raw.strip():
        return UsersFile()
    return UsersFile.model_validate_json(raw)


async def _save_unlocked(data: UsersFile) -> None:
    _ensure_dir()
    tmp = USERS_FILE.with_suffix(".json.tmp")
    payload = data.model_dump_json(indent=2)
    await asyncio.to_thread(tmp.write_text, payload, "utf-8")
    await asyncio.to_thread(tmp.replace, USERS_FILE)


async def get_user(email: str) -> User | None:
    async with _lock:
        data = await _load_unlocked()
        return data.users.get(email)


async def upsert_user(user: User) -> None:
    async with _lock:
        data = await _load_unlocked()
        data.users[user.email] = user
        await _save_unlocked(data)


async def update_tokens(email: str, tokens: OAuthTokens) -> None:
    async with _lock:
        data = await _load_unlocked()
        user = data.users.get(email)
        if user is None:
            raise KeyError(email)
        user.tokens = tokens
        await _save_unlocked(data)


async def set_broadcast(email: str, broadcast) -> None:
    async with _lock:
        data = await _load_unlocked()
        user = data.users.get(email)
        if user is None:
            raise KeyError(email)
        user.broadcast = broadcast
        await _save_unlocked(data)


async def clear_broadcast(email: str) -> None:
    await set_broadcast(email, None)
