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
    app_port: int = 8000
    log_level: str = "INFO"

    cors_allowed_origins: str = ""

    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db:  str = "ncfu_schedule"

    redis_url: str = "redis://redis:6379/0"

    # Cache TTLs (seconds)
    cache_ttl_now:      int = 60
    cache_ttl_day:      int = 600
    cache_ttl_week:     int = 900
    cache_ttl_search:   int = 300
    cache_ttl_overview: int = 300
    cache_ttl_meta:     int = 3600

    # Scraper
    base_url:               str   = "https://ecampus.ncfu.ru"
    scraper_concurrency:    int   = 5
    scraper_request_delay:  float = 0.4
    scrape_interval_hours:  int   = 1
    scrape_mode:            str   = "incremental"
    academic_year_start:    int   = 2025
    cron_timezone:          str   = "Europe/Moscow"
    otel_endpoint:          str   = ""

    backend_url: str = "http://backend:8000"
    backend_graphql_url: str = "http://backend:8000/graphql"

    telegram_bot_token:      SecretStr = SecretStr("")
    webhook_base_url:        str       = "https://yourdomain.com"
    support_bot_token:       SecretStr = SecretStr("")
    support_admin_chat_id:   int       = 0
    admin_bot_token:         SecretStr = SecretStr("")
    telegram_webhook_secret: SecretStr = SecretStr("")

    # logging
    default_message_limit:   int       = 300
    file_cache_ttl:          int       = 60

    openai_api_key: SecretStr

    # Auth
    auth_mongo_db:  str       = "ncfu_auth"
    jwt_secret:     SecretStr = SecretStr("")
    jwt_algorithm:  str       = "HS256"
    # Должен совпадать с backend config. Генерируется в setup-secrets.sh
    bot_api_secret: str       = ""
    web_url:        str       = ""

    # Static
    static_dir: str = "/app/static"

    dashboard_secret: SecretStr = SecretStr("")
    admin_path:       str       = ""

    graphql_secret: SecretStr = SecretStr("")

    sentry_dsn:         SecretStr = SecretStr("")
    sentry_traces_rate: float     = 0.1
    sentry_env:         str       = ""

    # Rate limiting
    rate_limit_user_rpm:   int = 120
    rate_limit_anon_rpm:   int = 30
    rate_limit_bot_rpm:    int = 20
    rate_limit_window:     int = 60
    webhook_rate_limit_rpm: int = 10
    flood_max_messages:    int = 5
    flood_window_secs:     int = 60
    quota_private:         int = 3
    quota_group_small:     int = 3
    quota_group_large:     int = 5
    quota_ttl_hours:       int = 7

    # Activity log retention
    activity_log_ttl_days: int = 90
    cleanup_hour_utc:      int = 3

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
        return self.openai_api_key.get_secret_value()


settings = Settings()
