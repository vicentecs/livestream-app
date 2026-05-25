from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    google_client_id: str = Field(..., alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., alias="GOOGLE_CLIENT_SECRET")
    app_secret_key: str = Field(..., alias="APP_SECRET_KEY")
    app_public_url: str = Field(..., alias="APP_PUBLIC_URL")
    restreamer_url: str = Field("http://restreamer:8080", alias="RESTREAMER_URL")
    restreamer_user: str = Field(..., alias="RESTREAMER_USER")
    restreamer_pass: str = Field(..., alias="RESTREAMER_PASS")
    rtsp_url: str = Field(..., alias="RTSP_URL")
    channel_prefix: str = Field("", alias="CHANNEL_PREFIX")
    court_number: str = Field("", alias="COURT_NUMBER")

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")


settings = Settings()
