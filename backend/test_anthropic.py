"""Test script to verify Anthropic API key and model access"""

import asyncio
import os
from dotenv import load_dotenv
# Note: If IDE shows import error, ensure Python interpreter is set to Poetry venv:
# Poetry venv path: C:\Users\jonel\AppData\Local\pypoetry\Cache\virtualenvs\bacolod-tourist-backend-sD2HPqzN-py3.13
# The import works correctly when run via: poetry run python test_anthropic.py
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

load_dotenv()

async def test_anthropic():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    
    print(f"Testing Anthropic API...")
    print(f"API Key present: {bool(api_key)}")
    print(f"API Key prefix: {api_key[:15] if api_key else 'N/A'}...")
    print(f"Model: {model}")
    print()
    
    if not api_key:
        print("❌ ERROR: ANTHROPIC_API_KEY not set in .env")
        return
    
    # Test different model names
    test_models = [
        "claude-3-5-sonnet",  # Without date suffix
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",  # With date
    ]
    
    for test_model in test_models:
        print(f"Testing model: {test_model}")
        try:
            llm = ChatAnthropic(
                model=test_model,
                anthropic_api_key=api_key,
                temperature=0.7,
            )
            response = await llm.ainvoke([HumanMessage(content="Say 'Hello'")])
            print(f"SUCCESS with model: {test_model}")
            print(f"   Response: {response.content[:50]}...")
            print()
            return test_model
        except Exception as e:
            error_str = str(e)
            if "404" in error_str or "not_found" in error_str.lower():
                print(f"X Model not found: {test_model}")
            elif "401" in error_str or "authentication" in error_str.lower():
                print(f"X Authentication failed - check your API key")
                break
            else:
                print(f"X Error: {error_str[:100]}")
            print()
    
    print("X None of the test models worked. Please check:")
    print("   1. Your API key is valid and starts with 'sk-ant-'")
    print("   2. Your Anthropic account has access to Claude models")
    print("   3. Your account is not on a restricted plan")

if __name__ == "__main__":
    asyncio.run(test_anthropic())

