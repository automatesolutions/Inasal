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
    
    # Dev Mode (skip OTP for testing)
    dev_mode: bool = True  # Set to False in production
    dev_mode_bypass_otp: bool = True  # Skip OTP verification in dev mode
    dev_mode_dummy_otp: str = "000000"  # Dummy OTP that always works in dev mode

    # LLM Provider Settings - Anthropic Claude only
    llm_provider: str = "anthropic"
    
    # Anthropic Claude
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"  # Working model for your account

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

    # RAG & Real-Time Data Settings
    weather_api_key: str = ""  # OpenWeatherMap API key
    weather_cache_ttl: int = 3600  # 1 hour
    events_cache_ttl: int = 1800  # 30 minutes
    news_cache_ttl: int = 3600  # 1 hour
    enable_weather_api: bool = False
    enable_events_api: bool = False

    # OAuth Settings
    oauth_base_url: str = "http://localhost:8000"  # Base URL for OAuth callbacks
    facebook_client_id: str = ""
    facebook_client_secret: str = ""
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    
    # Personality Inference Settings
    personality_inference_temperature: float = 0.3  # Lower temp for consistency
    
    # Behavior Tracking Settings
    behavior_update_interval_hours: int = 24  # Update personality every 24 hours
    min_interactions_for_update: int = 4  # Lower threshold for faster personality updates
    
    # Strapi Configuration
    strapi_url: str = "http://localhost:1337"
    strapi_api_token: str = ""  # API token for Strapi (create in Strapi admin panel)
    
    # Make.com Webhooks
    make_webhook_chat: str = ""  # Make.com chat workflow webhook URL
    make_webhook_recommendations: str = ""  # Make.com recommendations workflow webhook URL
    make_webhook_persona: str = ""  # Make.com persona discovery workflow webhook URL
    
    # Bright Data
    bright_data_api_key: str = ""  # Bright Data API token
    bright_data_base_url: str = "https://api.brightdata.com"  # Base URL for Bright Data API
    bright_data_collector_id: str = ""  # Optional collector identifier (deprecated, using datasets now)
    bright_data_timeout_seconds: int = 20  # Network timeout for Bright Data calls
    bright_data_reddit_search_dataset_id: str = "gd_lvz8ah06191smkebj4"  # Reddit search dataset ID
    bright_data_reddit_comments_dataset_id: str = "gd_lvzdpsdlw09j6t702"  # Reddit comments dataset ID
    bright_data_snapshot_poll_max_attempts: int = 60  # Max attempts to poll snapshot status
    bright_data_snapshot_poll_delay: int = 5  # Delay between poll attempts (seconds)
    # Bright Data MCP (optional - only needed for specific features)
    bright_data_web_unlocker_zone: str = ""  # Optional: Web Unlocker zone for proxy/unlocking
    bright_data_browser_auth: str = ""  # Optional: Browser authentication credentials

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env (like old OpenAI/Ollama settings)
    )


settings = Settings()
