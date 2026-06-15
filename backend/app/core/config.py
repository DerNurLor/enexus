from __future__ import annotations

from typing import Optional
from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env:  str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    cors_allowed_origins: str = ""

    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db:  str = "ncfu_schedule"

    redis_url: str = "redis://redis:6379/0"

    cache_ttl_now:      int = 60
    cache_ttl_day:      int = 600
    cache_ttl_week:     int = 900
    cache_ttl_search:   int = 300
    cache_ttl_overview: int = 300
    cache_ttl_meta:     int = 3600

    base_url:               str   = "https://ecampus.ncfu.ru"
    scraper_concurrency:    int   = 5
    scraper_request_delay:  float = 0.4
    scrape_interval_hours:  int   = 1
    scrape_mode:            str   = "incremental"
    academic_year_start:    int   = 2025
    cron_timezone:          str   = "Europe/Moscow"
    otel_endpoint:          str   = ""

    telegram_bot_token:      SecretStr = SecretStr("")
    webhook_base_url:        str       = "https://yourdomain.com"
    web_url:                 str       = ""
    support_bot_token:       SecretStr = SecretStr("")
    support_admin_chat_id:   int       = 0
    admin_bot_token:         SecretStr = SecretStr("")
    telegram_webhook_secret: SecretStr = SecretStr("")

    default_message_limit:   int       = 300
    file_cache_ttl:          int       = 60

    openai_api_key: Optional[SecretStr] = SecretStr("")

    auth_mongo_db:  str       = "ncfu_auth"
    jwt_secret:     SecretStr = SecretStr("")
    twocaptcha_api_key: str = ""
    # Генерируется автоматически в setup-secrets.sh
    bot_api_secret:     str = ""
    jwt_algorithm:  str       = "HS256"

    static_dir: str = "/app/static"

    dashboard_secret: SecretStr = SecretStr("")
    admin_path:       str       = ""

    graphql_secret: SecretStr = SecretStr("")

    sentry_dsn:         SecretStr = SecretStr("")
    sentry_traces_rate: float     = 0.1
    sentry_env:         str       = ""

    rate_limit_user_rpm:    int = 300
    rate_limit_anon_rpm:    int = 120
    rate_limit_bot_rpm:     int = 20
    rate_limit_window:      int = 60
    webhook_rate_limit_rpm: int = 10
    flood_max_messages:     int = 5
    flood_window_secs:      int = 60
    quota_private:          int = 3
    quota_group_small:      int = 3
    quota_group_large:      int = 5
    quota_ttl_hours:        int = 7

    activity_log_ttl_days: int = 90
    cleanup_hour_utc:      int = 3

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            jwt_val = self.jwt_secret.get_secret_value() if self.jwt_secret else ""
            if not jwt_val or len(jwt_val) < 32:
                raise ValueError(
                    "JWT_SECRET must be set and at least 32 characters in production. "
                    "Generate with: openssl rand -hex 64"
                )
        return self

    def get_telegram_bot_token(self) -> str:
        return self.telegram_bot_token.get_secret_value()

    def get_admin_bot_token(self) -> str:
        return self.admin_bot_token.get_secret_value()

    def get_support_bot_token(self) -> str:
        return self.support_bot_token.get_secret_value()

    def get_jwt_secret(self) -> str:
        return self.jwt_secret.get_secret_value()

    def get_graphql_secret(self) -> str:
        return self.graphql_secret.get_secret_value()

    def get_dashboard_secret(self) -> str:
        return self.dashboard_secret.get_secret_value()

    def get_telegram_webhook_secret(self) -> str:
        return self.telegram_webhook_secret.get_secret_value()

    def get_sentry_dsn(self) -> str:
        return self.sentry_dsn.get_secret_value()

    def get_openai_api_key(self) -> str:
        if not self.openai_api_key:
            return ""
        return self.openai_api_key.get_secret_value()


settings = Settings()
