import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


class Settings:
    @property
    def cors_origins(self) -> List[str]:
        raw = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", "")

    @property
    def openrouter_base_url(self) -> str:
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    @property
    def model(self) -> str:
        return os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


settings = Settings()
