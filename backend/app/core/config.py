from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings


class AIProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    LOCAL = "local"


class Settings(BaseSettings):
    app_name: str = "Nexora AI"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    database_url: str
    database_sync_url: str | None = None

    redis_url: str = "redis://localhost:6379/0"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "nexora_access"
    minio_secret_key: str = "nexora_secret"
    minio_bucket: str = "nexora-storage"
    minio_secure: bool = False

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    default_ai_provider: AIProvider = AIProvider.OPENROUTER

    cors_origins: str = "http://localhost:3000,http://localhost:5500"

    rate_limit_per_minute: int = 60

    max_file_size_mb: int = 50
    allowed_extensions: str = ".pdf,.docx,.doc,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.webp"

    ocr_enabled: bool = True
    agent_framework_enabled: bool = True
    agent_async_char_threshold: int = 2000

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}


settings = Settings()
