from pathlib import Path

from app.config import _API_DIR, _ENV_FILES, _REPO_DIR, get_settings
from app.db import _resolve_database_url


def test_env_files_include_repo_root():
    repo = Path(__file__).resolve().parents[3]
    api = Path(__file__).resolve().parents[1]
    assert _REPO_DIR == repo
    assert _API_DIR == api
    assert repo / ".env" in _ENV_FILES
    assert api / ".env" in _ENV_FILES
    # The old "../../.env" from apps/api pointed at the user home, not the repo.
    assert any(p.resolve() == (repo / ".env").resolve() for p in _ENV_FILES)


def test_bootstrap_configured_in_test_env():
    settings = get_settings()
    assert settings.bootstrap_configured is True


def test_relative_sqlite_url_pinned_to_api_dir():
    url = _resolve_database_url("sqlite+aiosqlite:///./havenid.db")
    assert url.startswith("sqlite+aiosqlite:///")
    assert url.endswith("havenid.db")
    assert _API_DIR.as_posix() in url.replace("\\", "/")
