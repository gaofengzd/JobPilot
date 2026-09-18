"""Environment settings; loading does not create clients or make network calls."""

from pathlib import Path
from typing import Literal

from pydantic import Field, HttpUrl, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_base_url: HttpUrl | None = None
    llm_structured_method: Literal["json_schema", "function_calling"] = "function_calling"
    llm_max_retries: int = Field(default=0, ge=0, le=2)
    embedding_model: str = ""
    embedding_api_key: SecretStr = SecretStr("")
    knowledge_dir: Path = PROJECT_ROOT / "data" / "knowledge"
    vector_index_dir: Path = PROJECT_ROOT / "data" / "vector_index"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    max_jobs: int = Field(default=20, ge=1, le=20)
    max_repair_attempts: int = Field(default=2, ge=0, le=2)
    request_timeout_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)

    def require_llm(self) -> None:
        missing = []
        if not self.llm_model.strip():
            missing.append("LLM_MODEL")
        if not self.llm_api_key.get_secret_value().strip():
            missing.append("LLM_API_KEY")
        if missing:
            raise ConfigurationError("Missing configuration: " + ", ".join(missing))


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        fields = sorted({str(error["loc"][0]) for error in exc.errors()})
        raise ConfigurationError("Invalid configuration fields: " + ", ".join(fields)) from None
