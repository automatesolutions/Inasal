"""FastAPI application entry point"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

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
    await connect_to_mongo()  # Will not fail if MongoDB unavailable
    try:
        await redis_client.connect()  # Will not fail if Redis unavailable
    except Exception:
        pass
    
    if HAS_LANGCHAIN and recommendation_engine:
        try:
            await recommendation_engine.initialize()
        except Exception as e:
            print(f"⚠️  Recommendation engine initialization failed: {e}")
    
    yield
    
    # Shutdown
    await close_mongo_connection()
    try:
        await redis_client.close()
    except Exception:
        pass


app = FastAPI(
    title="Bacolod Tourist API",
    description="AI-powered tourism API for Bacolod, Philippines",
    version="0.1.0",
    lifespan=lifespan,
)


class OptionsMiddleware(BaseHTTPMiddleware):
    """Handle OPTIONS requests explicitly for CORS preflight"""
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response(status_code=200)
            origin = request.headers.get("origin", "*")
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
            response.headers["Access-Control-Allow-Headers"] = request.headers.get("access-control-request-headers", "*")
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "3600"
            return response
        return await call_next(request)


# CORS middleware - add first (runs last, handles CORS)
# Get allowed origins from environment variable, default to localhost for development
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Add OPTIONS middleware LAST (runs FIRST, intercepts OPTIONS before CORS)
app.add_middleware(OptionsMiddleware)

# Include routers
app.include_router(auth_routes.router)
app.include_router(profile_routes.router)

# Include analytics routes
try:
    from app.routes import analytics_routes
    app.include_router(analytics_routes.router)
except ImportError:
    pass

# Include OAuth routes
try:
    from app.routes import oauth_routes
    app.include_router(oauth_routes.router)
except ImportError:
    print("⚠️  OAuth routes not available (authlib may not be installed)")

# Include LangChain-dependent routers if available
if HAS_LANGCHAIN:
    app.include_router(chat_routes.router)
    app.include_router(recommendation_routes.router)
    app.include_router(rag_routes.router)
else:
    # Add fallback routes that return proper errors when LangChain is not available
    from fastapi import HTTPException, status, Query, Depends
    from typing import Optional
    from app.auth import get_current_user
    
    @app.get("/api/recommendations")
    async def recommendations_fallback(
        limit: int = Query(default=10, ge=1, le=20),
        query: Optional[str] = None,
        current_user: dict = Depends(get_current_user),
    ):
        """Fallback endpoint when LangChain is not available"""
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not available. LangChain dependencies are not installed. Please install LangChain dependencies to enable AI features.",
        )
    
    @app.get("/api/recommendations/hidden-gems")
    async def hidden_gems_fallback(
        limit: int = Query(default=5, ge=1, le=10),
        current_user: dict = Depends(get_current_user),
    ):
        """Fallback endpoint when LangChain is not available"""
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is not available. LangChain dependencies are not installed. Please install LangChain dependencies to enable AI features.",
        )
    
    @app.post("/api/chat")
    async def chat_fallback(current_user: dict = Depends(get_current_user)):
        """Fallback endpoint when LangChain is not available"""
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is not available. LangChain dependencies are not installed. Please install LangChain dependencies to enable AI features.",
        )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Bacolod Tourist API", "status": "healthy"}


@app.get("/health")
async def health():
    """Detailed health check"""
    # TODO: Add actual health checks for MongoDB and Redis
    return {"status": "healthy", "service": "bacolod-tourist-api"}

