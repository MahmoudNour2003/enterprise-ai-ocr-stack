"""Application settings loaded from environment variables."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Get absolute path to enterprise-ai-ocr-stack root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Configuration settings for the Enterprise AI Proxy."""

    iti_api_key: str = ""
    iti_base_url: str = "http://apiaccess.iti.net.eg/api/v1"
    port: int = 8000
    allowed_models: str = "deepseek.v3.2,anthropic.claude-3-haiku-20240307-v1:0"
    max_retries: int = 3

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def get_allowed_model_ids(self) -> List[str]:
        """Returns parsed list of allowed model IDs."""
        if not self.allowed_models:
            return ["deepseek.v3.2", "anthropic.claude-3-haiku-20240307-v1:0"]
        return [m.strip() for m in self.allowed_models.split(",") if m.strip()]


settings = Settings()
