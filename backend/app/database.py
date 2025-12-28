"""Database connection and client setup"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database client"""

    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None


db = Database()
HAS_MONGODB = False


async def connect_to_mongo():
    """Create database connection - optional, won't fail if MongoDB unavailable"""
    global HAS_MONGODB
    try:
        db.client = AsyncIOMotorClient(
            settings.database_url,
            serverSelectionTimeoutMS=5000,
        )
        # Test connection
        await db.client.admin.command("ping")
        # Extract database name from URL
        db_name = settings.database_url.split("/")[-1].split("?")[0]
        db.database = db.client[db_name]
        HAS_MONGODB = True
        print(f"✅ Connected to MongoDB: {db_name}")
    except Exception as e:
        HAS_MONGODB = False
        print(f"⚠️  MongoDB not available: {e}")
        print("   Server will continue without MongoDB (using Strapi instead)")
        # Don't raise - allow server to start without MongoDB


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        print("✅ MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    if not HAS_MONGODB:
        raise RuntimeError("MongoDB is not available. Use Strapi instead.")
    return db.database

