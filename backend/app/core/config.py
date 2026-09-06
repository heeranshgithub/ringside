"""Application settings. The only module that reads the environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_SENSITIVE_MARKERS = ("key", "secret", "token", "password", "url", "uri", "phone")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    env: Literal["dev", "prod", "test"] = "dev"
    log_level: str = "INFO"
    cors_origins_raw: str = Field(default="http://localhost:3000", validation_alias="cors_origins")

    # Public URL of this backend (used to build webhook callback URLs). Empty = webhooks off.
    public_base_url: str = ""

    # Optional demo gate. When set, every /api request must carry X-Access-Code.
    app_access_code: str = ""

    # Mongo
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "ringside"

    # Hunar Voice Agents
    hunar_api_key: str = ""
    hunar_base_url: str = "https://api.voice.hunar.ai/external/v1"
    hunar_timezone: str = "Asia/Kolkata"

    # Safe dial: route every outbound call to a verified test number.
    safe_dial_mode: bool = True
    test_phone_numbers_raw: str = Field(default="", validation_alias="test_phone_numbers")

    # Let a visitor nominate their own phone as this session's safe-dial target, proven by a
    # short verification call. Off by default: with it on, the app will ring a number a
    # browser supplied, so it must never switch on by accident.
    allow_client_dial_target: bool = False
    dial_verify_per_number_per_day: int = 3
    dial_verify_per_session_per_day: int = 5
    dial_target_ttl_hours: int = 12
    dial_code_ttl_minutes: int = 10
    dial_code_max_attempts: int = 5

    # Background sync of non-terminal calls (fallback when webhooks cannot reach us).
    poller_enabled: bool = True
    poller_interval_seconds: int = 30

    # LLM via OpenRouter (OpenAI-compatible)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "anthropic/claude-sonnet-5"
    llm_audio_model: str = "google/gemini-2.5-flash"
    llm_app_name: str = "Ringside"

    # People search providers. PDL is the primary: 100 free searches a month, plus a
    # zero-credit sandbox with an identical schema for development.
    pdl_api_key: str = ""
    pdl_sandbox: bool = True
    coresignal_api_key: str = ""
    coresignal_max_collect: int = 10
    apollo_api_key: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def test_phone_numbers(self) -> list[str]:
        return [p.strip() for p in self.test_phone_numbers_raw.split(",") if p.strip()]

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def hunar_enabled(self) -> bool:
        return bool(self.hunar_api_key)

    @property
    def webhooks_enabled(self) -> bool:
        return bool(self.public_base_url)

    @property
    def client_dial_enabled(self) -> bool:
        """An access code is not optional here. Without one, anyone holding the URL could
        make the product ring an arbitrary phone, so the feature refuses to arm itself."""
        return self.allow_client_dial_target and bool(self.app_access_code)

    @property
    def client_dial_blocked_reason(self) -> str | None:
        if not self.allow_client_dial_target:
            return None
        if not self.app_access_code:
            return "ALLOW_CLIENT_DIAL_TARGET needs APP_ACCESS_CODE set as well"
        return None

    def redact(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, value in self.model_dump().items():
            sensitive = any(m in name for m in _SENSITIVE_MARKERS) and "base_url" not in name
            if sensitive and value:
                out[name] = "***" if not isinstance(value, list) else ["***"] * len(value)
            else:
                out[name] = value
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
