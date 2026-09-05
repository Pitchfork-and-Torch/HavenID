from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives at apps/api/app/config.py
# cwd-relative ".env" is not enough: uvicorn starts in apps/api, and the
# filled file is the monorepo root. The old "../../.env" pointed at $HOME.
_API_DIR = Path(__file__).resolve().parents[1]
_REPO_DIR = Path(__file__).resolve().parents[3]
_ENV_FILES = (
    Path.cwd() / ".env",
    _API_DIR / ".env",
    _REPO_DIR / ".env",
)


def _hydrate_env_files() -> None:
    """Load repo .env into os.environ without clobbering real process values.

    Empty exported vars (common after PowerShell .env import) must not wipe
    BOOTSTRAP_* from the file. pydantic-settings env_ignore_empty handles
    the Settings() pass; load_dotenv(override=False) covers import order.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in _ENV_FILES:
        if path.is_file():
            load_dotenv(dotenv_path=path, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    haven_env: str = "dev"
    haven_secret_key: str = "dev-secret-change-me"
    haven_data_key: str = ""
    haven_public_url: str = "http://localhost:3000"
    haven_domain: str = "localhost"
    cookie_secure: bool = False

    bootstrap_email: str = ""
    bootstrap_password: str = ""
    allow_signup: bool = False

    database_url: str = "sqlite+aiosqlite:///./havenid.db"
    redis_url: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_trial: bool = True

    xai_api_key: str = ""
    xai_model: str = "grok-4-1-fast"
    xai_api_base: str = "https://api.x.ai/v1"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    recordings_dir: str = "./data/recordings"

    access_ttl_seconds: int = 15 * 60
    refresh_ttl_seconds: int = 14 * 24 * 3600
    pending_ttl_seconds: int = 10 * 60

    @property
    def is_prod(self) -> bool:
        return self.haven_env.lower() in {"prod", "production"}

    @property
    def bootstrap_configured(self) -> bool:
        email = (self.bootstrap_email or "").strip()
        password = self.bootstrap_password or ""
        host = email.split("@")[-1] if "@" in email else ""
        return bool(email and "@" in email and "." in host and len(password) >= 8)

    @property
    def cookie_secure_effective(self) -> bool:
        if self.is_prod:
            return True
        return self.cookie_secure

    def recordings_path(self) -> Path:
        path = Path(self.recordings_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    _hydrate_env_files()
    return Settings()
