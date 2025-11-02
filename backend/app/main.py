"""FastAPI application entry point"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_to_mongo, close_mongo_connection
from app.redis_client import redis_client
from app.routes import auth_routes, profile_routes

# Conditionally import LangChain-dependent routes
try:
    from app.routes import chat_routes, recommendation_routes, rag_routes
    from app.recommendation import recommendation_engine
    HAS_LANGCHAIN = True
except ImportError as e:
    print(f"⚠️  LangChain dependencies not available: {e}")
    print("   Server will start without AI features (chat, recommendations, RAG)")
    HAS_LANGCHAIN = False
    recommendation_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    await connect_to_mongo()
    await redis_client.connect()
    if HAS_LANGCHAIN and recommendation_engine:
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
app.include_router(profile_routes.router)

# Include LangChain-dependent routers if available
if HAS_LANGCHAIN:
    app.include_router(chat_routes.router)
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

