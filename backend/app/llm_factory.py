"""LLM Factory - OpenAI"""

import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from app.config import settings

logger = logging.getLogger(__name__)


def get_chat_llm(temperature: float = 0.7, model: Optional[str] = None):
    """Get OpenAI LLM instance"""
    if not settings.openai_api_key:
        error_msg = "OPENAI_API_KEY not set in .env. Please configure your OpenAI API key."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    model_name = model or settings.openai_model
    
    # Common OpenAI model names
    supported_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]
    
    # Use the model name as-is
    try:
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=settings.openai_api_key,
        )
        logger.info(f"Initialized OpenAI LLM with model: {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI LLM with model '{model_name}': {e}")
        logger.error(f"API Key present: {bool(settings.openai_api_key)}")
        logger.error(f"API Key prefix: {settings.openai_api_key[:10] if settings.openai_api_key else 'N/A'}...")
        raise


def get_embeddings():
    """Get embeddings instance - returns None (embeddings not used in current setup)"""
    # Embeddings are not needed for LLM-only recommendation mode
    return None
