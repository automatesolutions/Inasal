"""Test all services connection"""

import asyncio
from app.bigquery_client import bigquery_client
from app.storage_client import storage_client
from app.redis_client import redis_client

async def test_all_services():
    """Test connection to all services"""
    print("Testing service connections...\n")
    
    # Test BigQuery
    try:
        await bigquery_client.connect()
        print(f"[SUCCESS] BigQuery: {'Connected' if bigquery_client._is_available() else 'Failed'}")
    except Exception as e:
        print(f"[FAILED] BigQuery: {e}")
    
    # Test Cloud Storage
    try:
        await storage_client.connect()
        print(f"[SUCCESS] Cloud Storage: {'Connected' if storage_client._is_available() else 'Failed'}")
    except Exception as e:
        print(f"[FAILED] Cloud Storage: {e}")
    
    # Test Redis
    try:
        await redis_client.connect()
        print(f"[SUCCESS] Redis: {'Connected' if redis_client.is_connected() else 'Failed'}")
    except Exception as e:
        print(f"[FAILED] Redis: {e}")
    
    print("\n[SUCCESS] All service tests completed!")

if __name__ == "__main__":
    asyncio.run(test_all_services())
