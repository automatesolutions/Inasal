"""Script to ingest attractions data into vector store"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.recommendation import RecommendationEngine


async def main():
    """Main ingestion function"""
    print("🚀 Starting attraction data ingestion...")
    
    engine = RecommendationEngine()
    await engine.initialize()
    
    if engine.vector_store:
        print(f"✅ Successfully ingested {len(engine.attractions_data)} attractions into vector store")
        print(f"📁 Vector store location: {Path('data/faiss_index').absolute()}")
    else:
        print("❌ Failed to create vector store. Check OpenAI API key configuration.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

