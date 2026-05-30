"""
Configuration management using pydantic-settings.

Core infra (DATABASE_URL, REDIS_URL) is required. Everything that feeds the
agent pipeline (Bright Data, LLM providers, MinIO) is optional with safe
defaults so the stack runs end-to-end in MOCK MODE without any credentials.
Drop real values into .env to switch to live calls.
"""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Core infra (required) ────────────────────────────────────────────────
    DATABASE_URL: str
    REDIS_URL: str

    # ── Bright Data ──────────────────────────────────────────────────────────
    # Residential proxy zone (used by Crawler + Web Unlocker fetch).
    BRIGHTDATA_API_KEY: str = ""
    BRIGHTDATA_CUSTOMER_ID: str = ""
    BRIGHTDATA_ZONE: str = ""                 # Web Unlocker zone (used via /request API)
    BRIGHTDATA_ZONE_PASSWORD: str = ""
    BRIGHTDATA_PROXY_HOST: str = "brd.superproxy.io"
    BRIGHTDATA_PROXY_PORT: int = 33335
    # Residential proxy zone — supports state/city/ZIP geo targeting (the demo axis)
    BRIGHTDATA_RESIDENTIAL_ZONE: str = ""
    BRIGHTDATA_RESIDENTIAL_PASSWORD: str = ""
    # Browser API (Scraping Browser) zone — drivable CDP endpoint for Journey Sim.
    BRIGHTDATA_BROWSER_ZONE: str = ""
    BRIGHTDATA_BROWSER_PASSWORD: str = ""
    BRIGHTDATA_BROWSER_HOST: str = "brd.superproxy.io"
    BRIGHTDATA_BROWSER_PORT: int = 9222
    # SERP API zone (Discovery agent — added later).
    BRIGHTDATA_SERP_ZONE: str = ""

    # ── Firecrawl (Crawler + Discovery structured extraction) ────────────────
    FIRECRAWL_API_KEY: str = ""
    FIRECRAWL_API_URL: str = "https://api.firecrawl.dev"   # self-host: set to your instance

    # CrewAI agent rate limit (requests/min) — respects provider limits.
    MAX_RPM: int = 18

    # ── LLM providers (Diff / Law-Mapper / Filing reasoning) ─────────────────
    # First configured provider in the fallback chain wins. PRD calls for
    # Claude Opus 4.7; Azure Kimi is supported because the team has a deployment.
    LLM_PROVIDER: str = "auto"                # auto | anthropic | kimi | azure_kimi | openai | mock
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-opus-4-7"
    # Direct Kimi / Moonshot platform (no Azure rate limits)
    KIMI_API_KEY: str = ""
    KIMI_ENDPOINT: str = "https://api.moonshot.ai/v1"
    KIMI_MODEL: str = "kimi-k2.5"
    # Azure-hosted Kimi
    AZURE_KIMI_ENDPOINT: str = ""
    AZURE_KIMI_KEY: str = ""
    AZURE_KIMI_MODEL: str = "Kimi-K2.5"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    # OpenAI-compatible gateway fallback (used when the primary LLM is rate-limited).
    AIMLAPI_KEY: str = ""
    AIMLAPI_ENDPOINT: str = "https://api.aimlapi.com/v1"
    AIMLAPI_MODEL: str = "gpt-4o"

    # ── Discovery / enrichment providers (optional, degrade gracefully) ──────
    # Web search provider for the Discovery agent (real URLs + snippets at runtime).
    WEB_SEARCH_API_KEY: str = ""
    # Knowledge-graph memory for cross-scan operator recall.
    COGNEE_API_KEY: str = ""
    # External-data query layer (analytics over scans).
    TRIGGERWARE_API_KEY: str = ""
    TRIGGERWARE_ENDPOINT: str = "https://api.triggerware.com"
    # Speech-to-text for voice scan commands.
    SPEECHMATICS_API_KEY: str = ""
    SPEECHMATICS_BATCH_URL: str = "https://asr.api.speechmatics.com/v2"

    # ── Evidence vault (S3-compatible: MinIO local OR Cloudflare R2 cloud) ────
    # STORAGE_BACKEND=minio uses the MINIO_* vars; =r2 uses the R2_* vars.
    # Both speak the S3 API, so the same client + presigned-URL logic serves both.
    STORAGE_BACKEND: str = "minio"            # minio | r2
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "fairprice-evidence"
    MINIO_SECURE: bool = False
    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""                   # -> https://<id>.r2.cloudflarestorage.com
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = "fairprice-evidence"
    R2_PUBLIC_BASE_URL: str = ""              # optional r2.dev / custom domain for public links

    # ── Scan behaviour ───────────────────────────────────────────────────────
    # Default two states for the geo-price split demo (Risk #1: stop before pay).
    DEFAULT_SCAN_STATES: str = "CA,TX"
    SCAN_STOP_BEFORE_PAYMENT: bool = True
    BRIGHTDATA_CREDIT_CAP: int = 500          # hard cap on live scans (PRD Risk #3)

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "FairPrice Watchdog"
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def default_states(self) -> List[str]:
        return [s.strip().upper() for s in self.DEFAULT_SCAN_STATES.split(",") if s.strip()]

    @property
    def brightdata_live(self) -> bool:
        """True when a residential proxy zone is configured (state/ZIP geo capable)."""
        return bool(self.BRIGHTDATA_CUSTOMER_ID and self.BRIGHTDATA_RESIDENTIAL_ZONE
                    and self.BRIGHTDATA_RESIDENTIAL_PASSWORD)

    @property
    def brightdata_unlocker_live(self) -> bool:
        """True when the Web Unlocker /request REST API is usable (Bearer token + zone)."""
        return bool(self.BRIGHTDATA_API_KEY and self.BRIGHTDATA_ZONE)

    @property
    def brightdata_unlocker_proxy_live(self) -> bool:
        """True when the Web Unlocker can be used in proxy mode with state geo
        (anti-bot bypass AND state/ZIP targeting in one)."""
        return bool(self.BRIGHTDATA_CUSTOMER_ID and self.BRIGHTDATA_ZONE and self.BRIGHTDATA_ZONE_PASSWORD)

    @property
    def brightdata_serp_live(self) -> bool:
        """True when the SERP /request REST API is usable."""
        return bool(self.BRIGHTDATA_API_KEY and self.BRIGHTDATA_SERP_ZONE)

    @property
    def brightdata_any_live(self) -> bool:
        return (self.brightdata_unlocker_proxy_live or self.brightdata_unlocker_live
                or self.brightdata_live or self.brightdata_browser_live)

    @property
    def brightdata_browser_live(self) -> bool:
        """True when Browser API credentials are present for live checkout walks."""
        return bool(self.BRIGHTDATA_CUSTOMER_ID and self.BRIGHTDATA_BROWSER_ZONE and self.BRIGHTDATA_BROWSER_PASSWORD)


# Global settings instance
settings = Settings()
