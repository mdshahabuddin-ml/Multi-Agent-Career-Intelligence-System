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

    # Hermes Agent
    HERMES_ENABLED: bool = True
    HERMES_MAX_CONCURRENT_TASKS: int = 10
    HERMES_DEFAULT_TIMEOUT: int = 300
    HERMES_MEMORY_LIMIT: int = 1000
    HERMES_SKILL_DIR: str = "data/hermes/skills"
    HERMES_TASK_DIR: str = "data/hermes/tasks"
    HERMES_MEMORY_DIR: str = "data/hermes/memory"

    # Content Engine
    CONTENT_ENGINE_ENABLED: bool = True
    CONTENT_DEFAULT_TONE: str = "professional"
    CONTENT_MAX_LENGTH: int = 5000

    # Social Integrations
    SOCIAL_ENABLED: bool = True
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    INSTAGRAM_CLIENT_ID: str = ""
    INSTAGRAM_CLIENT_SECRET: str = ""
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""
    FACEBOOK_REDIRECT_URI: str = ""
    GOOGLE_REDIRECT_URI: str = ""
    SOCIAL_TOKEN_KEY: str = ""

    # Video Generation (Google Veo)
    VIDEO_GENERATION_ENABLED: bool = True
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    VEO_MODEL: str = "veo-2.0-generate-001"
    VEO_REGION: str = "us-central1"
    VIDEO_OUTPUT_BUCKET: str = "careerintel-videos"
    VIDEO_MAX_SCENES: int = 5
    VIDEO_SCENE_DURATION_SECONDS: int = 8
    MOCK_VIDEO_GENERATION: bool = True

    # Observability (OpenTelemetry -> Phoenix). Disabled by default; the
    # backend/observability package no-ops unless OTEL_ENABLED is true.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "careerintel-backend"
    PHOENIX_OTLP_ENDPOINT: str = "http://localhost:4318/v1/traces"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()