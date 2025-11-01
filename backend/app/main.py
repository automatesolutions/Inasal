"""FastAPI application entry point"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_to_mongo, close_mongo_connection
from app.redis_client import redis_client
from app.routes import auth_routes, chat_routes, profile_routes, recommendation_routes, rag_routes
from app.recommendation import recommendation_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    await connect_to_mongo()
    await redis_client.connect()
    await recommendation_engine.initialize()
    yield
    # Shutdown
    await close_mongo_connection()
    await redis_client.close()


app = FastAPI(
    title="Bacolod Tourist API",
    description="AI-powered tourism API for Bacolod, Philippines",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(profile_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(rag_routes.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Bacolod Tourist API", "status": "healthy"}


@app.get("/health")
async def health():
    """Detailed health check"""
    # TODO: Add actual health checks for MongoDB and Redis
    return {"status": "healthy", "service": "bacolod-tourist-api"}

