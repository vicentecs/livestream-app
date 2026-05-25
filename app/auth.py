from datetime import datetime, timedelta, timezone

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

import storage
from config import settings
from models import OAuthTokens, User

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
]

REDIRECT_URI = f"{settings.app_public_url}/auth/callback"


def _build_flow(state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
    flow.redirect_uri = REDIRECT_URI
    return flow


def build_authorization_url() -> tuple[str, str]:
    flow = _build_flow()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


async def exchange_code_for_user(code: str, state: str) -> User:
    flow = _build_flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    if not creds.refresh_token:
        raise RuntimeError("Google não retornou refresh_token. Revogue o acesso em myaccount.google.com e tente novamente.")

    profile = await _fetch_userinfo(creds.token)

    tokens = OAuthTokens(
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        expiry=_aware(creds.expiry),
        scopes=list(creds.scopes or []),
    )
    user = User(
        email=profile["email"],
        name=profile.get("name", profile["email"]),
        picture=profile.get("picture"),
        tokens=tokens,
    )
    await storage.upsert_user(user)
    return user


async def _fetch_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        r.raise_for_status()
        return r.json()


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def ensure_valid_token(user: User) -> Credentials:
    creds = Credentials(
        token=user.tokens.access_token,
        refresh_token=user.tokens.refresh_token,
        token_uri=user.tokens.token_uri,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=user.tokens.scopes,
    )
    creds.expiry = user.tokens.expiry.replace(tzinfo=None)

    now = datetime.now(timezone.utc)
    expiry = _aware(user.tokens.expiry)
    if expiry - now > timedelta(minutes=5):
        return creds

    import asyncio
    await asyncio.to_thread(creds.refresh, Request())

    user.tokens = OAuthTokens(
        access_token=creds.token,
        refresh_token=creds.refresh_token or user.tokens.refresh_token,
        token_uri=creds.token_uri,
        expiry=_aware(creds.expiry),
        scopes=user.tokens.scopes,
    )
    await storage.update_tokens(user.email, user.tokens)
    return creds
