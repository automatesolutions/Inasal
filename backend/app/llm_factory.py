"""LLM Factory - Anthropic Claude only"""

import logging
from typing import Optional
from langchain_anthropic import ChatAnthropic
from app.config import settings

logger = logging.getLogger(__name__)


def get_chat_llm(temperature: float = 0.7, model: Optional[str] = None):
    """Get Anthropic Claude LLM instance"""
    if not settings.anthropic_api_key:
        error_msg = "ANTHROPIC_API_KEY not set in .env. Please configure your Anthropic API key."
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    model_name = model or settings.anthropic_model
    
    # Try common model name formats if the configured one fails
    # langchain-anthropic might use different model names than the raw API
    model_aliases = {
        "claude-3-opus-20240229": "claude-3-opus-20240229",
        "claude-3-sonnet-20240229": "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307": "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620": "claude-3-5-sonnet-20240620",
    }
    
    # Use the model name as-is, langchain-anthropic should handle it
    try:
        llm = ChatAnthropic(
            model=model_name,
            temperature=temperature,
            anthropic_api_key=settings.anthropic_api_key,
        )
        logger.info(f"Initialized Claude LLM with model: {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize Claude LLM with model '{model_name}': {e}")
        logger.error(f"API Key present: {bool(settings.anthropic_api_key)}")
        logger.error(f"API Key prefix: {settings.anthropic_api_key[:10] if settings.anthropic_api_key else 'N/A'}...")
        raise


def get_embeddings():
    """Get embeddings instance - returns None (embeddings not used with Anthropic-only setup)"""
    # Embeddings are not needed for LLM-only recommendation mode
    return None
