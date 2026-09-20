"""Application settings.

Every value has a default that works offline, so the whole system runs with no
environment file and no API keys. Only deployment needs configuration.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="COUNTERSIGN_", extra="ignore")

    # Storage. SQLite by default so a clone runs without a database server.
    database_url: str = "sqlite+aiosqlite:///./countersign.db"
    storage_dir: str = "data/storage"

    # Extraction. "mock" replays committed fixtures and needs no network.
    llm_provider: str = "mock"
    llm_model: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""
    prompt_version: str = "v2"
    extraction_timeout_s: int = 60
    extraction_max_retries: int = 1

    # A field below this confidence sends the invoice to review even if the
    # arithmetic validators pass.
    min_field_confidence: float = 0.75

    # Three-way match. Quantity must be exact; price carries a tolerance because
    # rounding and freight allocation move unit prices by small amounts.
    price_tolerance_pct: Decimal = Decimal("2.0")
    description_match_threshold: float = 0.82

    # Price variance. Below the minimum history the check abstains rather than
    # reporting a number derived from too few observations.
    price_history_window_days: int = 365
    price_history_min_points: int = 5
    price_variance_mad_threshold: Decimal = Decimal("3.5")

    # Duplicate detection.
    near_duplicate_window_days: int = 45

    # Tax. Two decimal places, half-up, applied at every step.
    money_places: int = 2

    # Agent bounds. Both are hard caps, asserted by tests.
    agent_max_steps: int = 12
    agent_max_tool_calls: int = 20

    corpus_seed: int = Field(default=20260920, description="Seed for the synthetic corpus")


settings = Settings()
