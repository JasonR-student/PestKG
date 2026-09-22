from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PESTKG_", env_file=".env", extra="ignore"
    )

    release_id: str | None = "2026.08.3_federated"
    data_dir: Path = Field(default=Path("data/releases"))
    state_dir: Path = Field(default=Path("data/state"))
    download_dir: Path | None = None
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    export_limit: int = 100_000
    graph_node_limit: int = 1_000
    graph_edge_limit: int = 2_000
    repository_cache_size: int = Field(default=3, ge=1, le=12)

    neo4j_uri: str | None = None
    neo4j_user: str = "neo4j"
    neo4j_password: str | None = None

    @property
    def release_dir(self) -> Path:
        if self.release_id is None:
            raise ValueError("PESTKG_RELEASE_ID is not configured")
        return self.data_dir / self.release_id

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin]

    @property
    def resolved_download_dir(self) -> Path:
        return self.download_dir or self.release_dir / "downloads"


@lru_cache
def get_settings() -> Settings:
    return Settings()
