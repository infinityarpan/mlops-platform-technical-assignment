from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./mlops.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    log_level: str = "INFO"
    deploy_step_delay_seconds: float = 0.2
    eager_tasks: bool = False
    mlflow_tracking_uri: str = "sqlite:///./mlflow.db"
    backend_url: str = "http://localhost:8000"
    prometheus_url: str = "http://localhost:9090"
    pushgateway_url: str = "http://localhost:9091"
    prometheus_metrics_lookback_days: int = 30
    prometheus_query_step: str = "5m"
    metrics_seed_interval_seconds: float = 0.5
    metrics_degraded_error_rate: float = 0.02
    metrics_degraded_drift_score: float = 0.3
    drift_data_dir: Path = Path("data/drift")


settings = Settings()
