"""
dashboard/app/core/config.py

Settings for the standalone Dashboard service.
"""
from __future__ import annotations

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env:  str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8003
    log_level: str = "INFO"

    cors_allowed_origins: str = ""

    # MongoDB — shared with Backend
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db:  str = "ncfu_schedule"
    auth_mongo_db: str = "ncfu_auth"

    # Redis — shared with Backend
    redis_url: str = "redis://redis:6379/0"

    # Telegram (for media proxy and sending messages)
    telegram_bot_token:  SecretStr = SecretStr("")
    admin_bot_token:     SecretStr = SecretStr("")

    # Auth (must match Backend JWT_SECRET)
    jwt_secret:    SecretStr = SecretStr("")
    jwt_algorithm: str       = "HS256"

    # Dashboard access
    dashboard_secret: SecretStr = SecretStr("")
    admin_path:       str       = ""
    webhook_base_url:     str       = "https://yourdomain.com"

    # Static files
    static_dir: str = "/app/static"

    # Rate limiting (used by ratelimit middleware in dependencies)
    rate_limit_user_rpm:   int = 120
    rate_limit_anon_rpm:   int = 30
    rate_limit_window:     int = 60

    # Message quota (must match ecampus_bot config)
    quota_private:     int = 3
    quota_group_small: int = 3
    quota_group_large: int = 5
    quota_ttl_hours:   int = 7

    # Logging
    activity_log_ttl_days: int = 90
    cleanup_hour_utc:      int = 3

    # Observability
    sentry_dsn:         SecretStr = SecretStr("")
    sentry_traces_rate: float     = 0.1
    sentry_env:         str       = ""
    otel_endpoint:      str       = ""

    # ── Convenience helpers ───────────────────────────────────────────────────

    def get_telegram_bot_token(self) -> str:
        return self.telegram_bot_token.get_secret_value()

    def get_admin_bot_token(self) -> str:
        return self.admin_bot_token.get_secret_value()

    def get_jwt_secret(self) -> str:
        return self.jwt_secret.get_secret_value()

    def get_dashboard_secret(self) -> str:
        return self.dashboard_secret.get_secret_value()

    def get_sentry_dsn(self) -> str:
        return self.sentry_dsn.get_secret_value()

    # Stub methods used by imported modules (dashboard api.py etc.)
    def get_graphql_secret(self) -> str:
        return ""

    def get_telegram_webhook_secret(self) -> str:
        return ""

    def get_openai_api_key(self) -> str:
        return ""

    def get_support_bot_token(self) -> str:
        return ""


settings = Settings()

# Add after existing settings - need this for avatar URL generation
