from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str = "postgresql://nml:nml_dev_password@localhost:5432/nml_shelf"

    salla_client_id: str = ""
    salla_client_secret: str = ""
    salla_refresh_token: str = ""
    salla_store_name: str = "mock-store"
    salla_store_url: str = ""
    salla_token_url: str = "https://accounts.salla.sa/oauth2/token"
    salla_api_base_url: str = "https://api.salla.dev/admin/v2"

    orbit_mock_mode: bool = True
    orbit_run_initial_pull: bool = True
    orbit_salla_poll_interval_minutes: int = 15
    orbit_ad_poll_interval_minutes: int = 60

    meta_ad_library_access_token: str = ""

    # Genome — text embedding model must output TEXT_EMBEDDING_DIM dimensions (768)
    genome_embedding_model: str = "intfloat/multilingual-e5-base"
    # Calibrated against multilingual-e5-base on KSA Arabic food product titles:
    # same-product pairs score ≥0.983; different-product pairs top out at ~0.928.
    # 0.97 auto-applies near-identical text; 0.94 queues plausible-same for review.
    genome_high_confidence_threshold: float = 0.97
    genome_review_threshold: float = 0.94

    atlas_mock_mode: bool = True

    # Oracle Phase 1 — weighted scorer (no ML until ledger has real approve/reject volume)
    # Weights must be set intentionally; they don't need to sum to 1.0 but the team
    # should understand the relative emphasis each signal gets.
    oracle_weight_velocity: float = 0.30      # listing count across stores (demand proxy)
    oracle_weight_ad_intensity: float = 0.25  # active ad count matched to product
    oracle_weight_category_gap: float = 0.25  # placeholder — no stocking data yet
    oracle_weight_price_fit: float = 0.20     # price vs. cluster income tier
    oracle_top_k: int = 5                     # how many ranked candidates to return

    # Pulse — spike detection thresholds
    # How far back to look for the baseline period (one full window before current)
    pulse_spike_window_hours: int = 24
    # Alert when current count >= this multiple of the baseline average
    pulse_spike_min_ratio: float = 2.0
    # Don't alert on signals whose current count is below this — filters out noise
    # from very low-volume terms where a 1→2 jump looks like a 100% spike
    pulse_spike_min_absolute: int = 3

    log_level: str = "INFO"


settings = Settings()
