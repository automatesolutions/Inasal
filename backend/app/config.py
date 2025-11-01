"""Application configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    database_url: str = "mongodb://localhost:27017/bacolod_tourist"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    openai_embedding_model: str = "text-embedding-3-small"  # Cost-effective embedding model

    # Email (for OTP)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Vector Store
    vector_store_path: str = "data/faiss_index"
    vector_store_type: str = "faiss"  # "faiss" or "pinecone"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "bacolod-attractions"
    pinecone_environment: str = "us-east1-gcp"

    # Recommendation Settings
    default_recommendation_limit: int = 10
    max_recommendation_limit: int = 20
    embedding_dimension: int = 1536  # OpenAI text-embedding-3-small dimension

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
