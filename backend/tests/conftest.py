"""Pytest configuration and fixtures"""

import pytest
from app.database import connect_to_mongo, close_mongo_connection
from app.redis_client import redis_client
from app.user_profile import UserProfileService


@pytest.fixture(scope="session")
async def db_setup():
    """Set up database connection for tests"""
    try:
        await connect_to_mongo()
        await redis_client.connect()
        yield
    finally:
        await close_mongo_connection()
        await redis_client.close()


@pytest.fixture
async def cleanup_db(db_setup):
    """Clean up test data after each test"""
    yield
    # Clean up test profiles
    service = UserProfileService()
    db = service.get_database() if hasattr(service, 'get_database') else None
    if db:
        await db[UserProfileService.COLLECTION_NAME].delete_many({
            "user_id": {"$regex": "^(test-|get-|personality-|prefs-|log-|history-)"}
        })
        await db["interaction_logs"].delete_many({
            "user_id": {"$regex": "^(test-|log-|history-)"}
        })

