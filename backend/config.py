from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Multi-Agent Career Intelligence System"

    APP_ENV: str = "development"

    DEBUG: bool = True

    BACKEND_HOST: str = "0.0.0.0"

    BACKEND_PORT: int = 8000

    DATABASE_URL: str = (
        "postgresql://careerintel:careerintel@localhost:5432/careerintel"
    )

    SECRET_KEY: str = "development-secret-key"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ALGORITHM: str = "HS256"

    OPENAI_API_KEY: str = ""

    OPENAI_MODEL: str = "gpt-4o-mini"

    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    FRONTEND_URL: str = "http://localhost:5173"

    MAX_RESEARCH_SOURCES: int = 10

    RESEARCH_TIMEOUT_SECONDS: int = 30

    MAX_CONCURRENT_RESEARCH_TASKS: int = 5

    MAX_FILE_SIZE_MB: int = 10

    ALLOWED_EXTENSIONS: str = "pdf,doc,docx,txt"

    QDRANT_URL: str = "http://localhost:6333"

    QDRANT_API_KEY: str = ""

    QDRANT_COLLECTION: str = "careerintel"

    REDIS_URL: str = "redis://localhost:6379/0"

    TAVILY_API_KEY: str = ""

    SERPER_API_KEY: str = ""

    NEWSAPI_KEY: str = ""

    GITHUB_TOKEN: str = ""

    SMTP_HOST: str = ""

    SMTP_PORT: int = 587

    SMTP_USER: str = ""

    SMTP_PASSWORD: str = ""

    EMAIL_FROM: str = "noreply@careerintel.ai"

    # Data Pipeline
    MOCK_DATA: bool = True
    DATA_PIPELINE_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()