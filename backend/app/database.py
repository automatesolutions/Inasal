"""Database connection and client setup"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure

from app.config import settings


class Database:
    """MongoDB database client"""

    client: AsyncIOMotorClient = None
    database: AsyncIOMotorDatabase = None


db = Database()


async def connect_to_mongo():
    """Create database connection"""
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
        print(f"✅ Connected to MongoDB: {db_name}")
    except ConnectionFailure as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        print("✅ MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance"""
    return db.database

