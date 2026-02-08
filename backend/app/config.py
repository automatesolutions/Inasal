"""Application configuration"""

from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Google Cloud Platform
    gcp_project_id: str = ""
    gcp_credentials_path: str = ""  # Path to service account JSON file
    bigquery_dataset_id: str = "bacolod_tourist"
    gcs_bucket_name: str = "bacolod-tourist-storage"
    gcs_bucket_location: str = "us-central1"

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

    # LLM Provider Settings - OpenAI
    llm_provider: str = "openai"
    
    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"  # Default OpenAI model (gpt-4o-mini, gpt-4o, gpt-3.5-turbo)

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
    
    # Make.com Webhooks
    make_webhook_chat: str = ""  # Make.com chat workflow webhook URL
    make_webhook_recommendations: str = ""  # Make.com recommendations workflow webhook URL
    make_webhook_persona: str = ""  # Make.com persona discovery workflow webhook URL
    
    # Bright Data
    # Note: Pydantic Settings looks for BRIGHT_DATA_API_KEY by default
    # But we also support BRIGHT_DATA_API_TOKEN for compatibility
    bright_data_api_key: str = ""
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
    bright_data_serp_zone: str = ""  # Optional: SERP API zone (e.g., "serp_api2") for Google/Bing searches
    bright_data_serp_api_key: str = ""  # Optional: Separate API key for SERP API
    
    # Bright Data Residential Proxy (for Scrapy)
    bright_data_zone: str = ""  # Zone name (e.g., "webscrape_amzn")
    bright_data_residential_username: str = ""  # Full username (e.g., "brd-customer-hl_c2b71bb6-zone-webscraperamzn__proxy1")
    bright_data_residential_password: str = ""  # Password for residential proxy
    bright_data_residential_endpoint: str = "brd.superproxy.io:33335"  # Proxy endpoint (default: brd.superproxy.io:33335)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env (like old OpenAI/Ollama settings)
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # If bright_data_api_key is empty, check for BRIGHT_DATA_API_TOKEN
        # (Pydantic Settings looks for BRIGHT_DATA_API_KEY by default)
        if not self.bright_data_api_key:
            self.bright_data_api_key = os.getenv('BRIGHT_DATA_API_TOKEN', '')
        # If bright_data_serp_api_key is empty, check for BRIGHT_DATA_SERP_API_KEY
        if not self.bright_data_serp_api_key:
            self.bright_data_serp_api_key = os.getenv('BRIGHT_DATA_SERP_API_KEY', '')
        # If bright_data_serp_zone is empty, check for BRIGHT_DATA_SERP_ZONE, or default to "serp_api2"
        if not self.bright_data_serp_zone:
            self.bright_data_serp_zone = os.getenv('BRIGHT_DATA_SERP_ZONE', 'serp_api2')
        # If openai_api_key is empty, check for OPENAI_API_KEY
        if not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY', '')


settings = Settings()
