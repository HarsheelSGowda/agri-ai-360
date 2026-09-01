from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "sqlite:///./agriai.db"
    secret_key: str = "dev-only-insecure-key-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    frontend_origin: str = "http://localhost:5173"
    weather_api_key: str = ""
    weather_provider: str = "mock"
    models_dir: str = "../models"

    @property
    def resolved_models_dir(self) -> Path:
        path = Path(self.models_dir)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        return path


settings = Settings()
