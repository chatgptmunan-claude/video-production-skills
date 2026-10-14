from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PKG_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PKG_ROOT / "artifacts"
DATA_DIR = PKG_ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAD_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{(DATA_DIR / 'pad.sqlite3').as_posix()}"
    http_timeout: float = 25.0
    http_user_agent: str = (
        "Mozilla/5.0 (compatible; PinterestAnimalDedup/0.1; +https://github.com/local)"
    )
    request_delay_seconds: float = 0.75
    pinterest_max_pins_per_query: int = 12
    discover_target_count: int = 20
    dedup_queries_per_platform: int = 5
    visual_hamming_threshold: int = 12
    searx_url: str = ""

    @classmethod
    def ensure_dirs(cls) -> "Settings":
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return cls()


settings = Settings.ensure_dirs()
