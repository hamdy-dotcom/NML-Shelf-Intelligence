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

    log_level: str = "INFO"


settings = Settings()
