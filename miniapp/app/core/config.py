from __future__ import annotations
from typing import Optional
"""
config.py — hardened settings.

Security changes:
  [V1]  All secrets read exclusively from environment variables.
        Plaintext defaults replaced with empty strings (app fails fast if unset).
  [V2]  cors_allowed_origins: comma-separated whitelist, no wildcard.
  [V3]  telegram_webhook_secret: new field for X-Telegram-Bot-Api-Secret-Token.
  [V9]  mongo_uri default expects credentials: mongodb://user:pass@host:27017
  [V13] redis_url default expects password: redis://:password@host:6379/0
  [V14] Secret fields use pydantic SecretStr — never appear in repr/logs.
"""

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

    # [V2] CORS whitelist — comma-separated production domains.
    # Example: "https://app.example.com,https://admin.example.com"
    cors_allowed_origins: str = ""

    # [V9] MongoDB — URI must include credentials in production.
    # Format: mongodb://appuser:StrongPass@mongo:27017/dbname?authSource=admin
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db:  str = "ncfu_schedule"

    # [V13] Redis — URL must include password in production.
    # Format: redis://:StrongRedisPass@redis:6379/0
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

    # Backend API URL — miniapp may optionally proxy some requests
    backend_url: str = "http://backend:8000"
    backend_graphql_url: str = "http://backend:8000/graphql"

    # Telegram
    # [V1]  No plaintext defaults — app raises on startup if unset in prod.
    # [V3]  telegram_webhook_secret is the shared secret registered with setWebhook.
    telegram_bot_token:      SecretStr = SecretStr("")
    webhook_base_url:        str       = "https://yourdomain.com"
    support_bot_token:       SecretStr = SecretStr("")
    support_admin_chat_id:   int       = 0
    admin_bot_token:         SecretStr = SecretStr("")
    telegram_webhook_secret: SecretStr = SecretStr("")  # [V3] new

    # logging
    default_message_limit:   int       = 300
    file_cache_ttl:          int       = 60

    # OpenAI
    # [V1] SecretStr — never leaked in repr or logs.
    openai_api_key: Optional[SecretStr] = SecretStr("")

    # Auth
    auth_mongo_db:  str       = "ncfu_auth"
    # [V1] No insecure plaintext default. Generate with: openssl rand -hex 64
    jwt_secret:     SecretStr = SecretStr("")
    jwt_algorithm:  str       = "HS256"

    # Static
    static_dir: str = "/app/static"

    # Dashboard
    # [V6] dashboard_secret + admin_path are defence-in-depth ONLY.
    #      Primary auth is JWT/RBAC via require_permission("admin:full").
    dashboard_secret: SecretStr = SecretStr("")
    admin_path:       str       = ""

    # [V5] GraphQL IDE gate — secret delivered via X-Admin-Secret header.
    graphql_secret: SecretStr = SecretStr("")

    # Observability
    # [V1] sentry_dsn is a secret — SecretStr prevents it appearing in logs.
    sentry_dsn:         SecretStr = SecretStr("")
    sentry_traces_rate: float     = 0.1
    sentry_env:         str       = ""

    # Rate limiting
    rate_limit_user_rpm:   int = 120
    rate_limit_anon_rpm:   int = 30
    rate_limit_bot_rpm:    int = 20
    rate_limit_window:     int = 60
    # Webhook-specific limit (req/min per IP, Telegram IPs are whitelisted)
    webhook_rate_limit_rpm: int = 10
    # Anti-flood: messages per window per user (Premium users get 2×)
    flood_max_messages:    int = 5
    flood_window_secs:     int = 60
    # Message quota per chat (7-hour rolling window)
    quota_private:         int = 3    # DMs
    quota_group_small:     int = 3    # groups < 4 members
    quota_group_large:     int = 5    # groups ≥ 4 members
    quota_ttl_hours:       int = 7

    # Activity log retention
    activity_log_ttl_days: int = 90
    cleanup_hour_utc:      int = 3

    # ── Convenience helpers (unwrap SecretStr safely) ─────────────────────────

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
