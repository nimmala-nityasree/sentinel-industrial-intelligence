"""
Centralized application configuration.

All environment-driven settings live here as a single typed Settings object.
Every module in the codebase imports `settings` from this file rather than
calling os.getenv() directly — this keeps configuration auditable in one
place and gives us validation (via pydantic) for free.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings sourced from environment variables / .env."""

    # ---- LLM provider (Gemini) ----
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "models/text-embedding-004"

    # ---- Neo4j knowledge graph ----
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "sentinel_pass"

    # ---- Vector store (Chroma) ----
    chroma_persist_dir: str = "./data/chroma_store"
    chroma_collection_name: str = "sentinel_documents"

    # ---- OCR ----
    tesseract_cmd: str = "/usr/bin/tesseract"
    ocr_language: str = "eng"

    # ---- App / server ----
    app_env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:8501"

    # ---- Agent decision thresholds ----
    min_answer_confidence: float = 0.55
    drift_detection_lookback_days: int = 730

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS is a comma-separated string in .env; expose it as a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor.

    lru_cache ensures the .env file is parsed exactly once per process rather
    than on every import, while still allowing tests to override via
    get_settings.cache_clear() + monkeypatched environment variables.
    """
    return Settings()


settings = get_settings()
