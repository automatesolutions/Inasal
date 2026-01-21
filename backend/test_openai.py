"""Test script to verify OpenAI API key and model access"""

import os
import asyncio
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# The import works correctly when run via: poetry run python test_openai.py
from langchain_openai import ChatOpenAI


async def test_openai():
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    print(f"Testing OpenAI API...")
    print(f"Model: {model}")
    print(f"API Key: {'[SET]' if api_key else '[NOT SET]'}")
    if api_key:
        print(f"API Key prefix: {api_key[:20]}...")
    print()
    
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        print("   Please add OPENAI_API_KEY=your_key_here to backend/.env")
        print(f"   Current working directory: {os.getcwd()}")
        print(f"   Looking for .env in: {os.path.join(os.getcwd(), '.env')}")
        return False
    
    # Try different model names
    models_to_try = [
        model,  # Try configured model first
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]
    
    for model_name in models_to_try:
        try:
            print(f"Testing model: {model_name}...")
            llm = ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                temperature=0.7,
            )
            
            # Test a simple prompt
            response = await llm.ainvoke("Say 'Hello, OpenAI!' in one sentence.")
            print(f"[SUCCESS] Response: {response.content}")
            print()
            print("[SUCCESS] OpenAI API is working correctly!")
            print()
            print("Next steps:")
            print("   1. Your OpenAI API key is valid")
            print("   2. Your OpenAI account has access to GPT models")
            print(f"   3. Model '{model_name}' is available")
            return True
            
        except Exception as e:
            print(f"   [FAILED] {e}")
            continue
    
    print("[ERROR] All models failed. Please check your API key and account access.")
    return False


if __name__ == "__main__":
    asyncio.run(test_openai())
