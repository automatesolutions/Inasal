"""FastAPI application entry point"""

import os
import json
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.redis_client import redis_client
from app.bigquery_client import bigquery_client
from app.storage_client import storage_client
from app.routes import auth_routes, profile_routes

logger = logging.getLogger(__name__)

# Conditionally import LangChain-dependent routes
try:
    from app.routes import chat_routes, recommendation_routes, rag_routes
    from app.recommendation import recommendation_engine
    HAS_LANGCHAIN = True
except ImportError as e:
    logger.warning(f"LangChain dependencies not available: {e}")
    logger.info("Server will start without AI features (chat, recommendations, RAG)")
    HAS_LANGCHAIN = False
    recommendation_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    # Initialize Google Cloud services (BigQuery and Cloud Storage)
    try:
        await bigquery_client.connect()
    except Exception as e:
        logger.warning(f"BigQuery not available: {e}")
    
    try:
        await storage_client.connect()
    except Exception as e:
        logger.warning(f"Cloud Storage not available: {e}")
    
    try:
        await redis_client.connect()  # Will not fail if Redis unavailable
    except Exception:
        pass
    
    if HAS_LANGCHAIN and recommendation_engine:
        try:
            await recommendation_engine.initialize()
        except Exception as e:
            logger.error(f"Recommendation engine initialization failed: {e}")
    
    # Start background BigQuery retry task
    try:
        from app.bigquery_retry_queue import start_background_retry_task
        background_retry_task = start_background_retry_task()
        logger.info("Background BigQuery retry task started")
    except Exception as e:
        logger.warning(f"Failed to start background retry task: {e}")
        background_retry_task = None
    
    yield
    
    # Shutdown
    try:
        await redis_client.close()
    except Exception:
        pass
    
    # Cancel background task
    if background_retry_task:
        try:
            background_retry_task.cancel()
            logger.info("Background BigQuery retry task stopped")
        except Exception:
            pass


app = FastAPI(
    title="Bacolod Tourist API",
    description="AI-powered tourism API for Bacolod, Philippines",
    version="0.1.0",
    lifespan=lifespan,
)


# Removed OptionsMiddleware - CORS middleware handles OPTIONS requests


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests for debugging"""
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/auth/send-otp"):
            logger.info(f"INCOMING REQUEST: {request.method} {request.url.path}")
        return await call_next(request)


# CORS middleware - add first (runs last, handles CORS)
# Get allowed origins from environment variable, default to localhost for development
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,*")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

logger.info(f"CORS Allowed Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors - return detailed error messages"""
    errors = exc.errors()
    
    logger.error(f"VALIDATION ERROR in {request.method} {request.url.path}:")
    logger.error(f"   Number of errors: {len(errors)}")
    # Convert errors to JSON-serializable format
    try:
        logger.error(f"   Errors: {json.dumps([str(e) for e in errors], indent=2)}")
    except Exception:
        logger.error(f"   Errors: (unable to serialize)")
    try:
        body = await request.body()
        logger.error(f"   Request Body: {body.decode('utf-8') if body else 'Empty'}")
    except Exception as e:
        logger.error(f"   Could not read body: {e}")
    
    # Extract detailed error messages
    error_messages = []
    for error in errors:
        # Get field location (skip 'body' prefix if present)
        loc = error.get('loc', [])
        # Filter out 'body' from location path for cleaner messages
        field_parts = [str(l) for l in loc if l != 'body']
        field = '.'.join(field_parts) if field_parts else 'input'
        
        msg = error.get('msg', 'Invalid value')
        error_type = error.get('type', '')
        
        # Create user-friendly error message
        if field and field != 'input':
            error_messages.append(f"{field}: {msg}")
        else:
            error_messages.append(msg)
    
    # Always return detailed errors, never generic message
    if error_messages:
        error_detail = '. '.join(error_messages)
    else:
        # Fallback: return the raw error structure if parsing failed
        error_detail = f"Validation failed: {json.dumps(errors)}"
    
    return Response(
        status_code=422,
        content=json.dumps({"detail": error_detail}),
        media_type="application/json"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions (except HTTPException which FastAPI handles)"""
    # Don't catch HTTPException - let FastAPI handle it
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        raise exc
    
    error_traceback = traceback.format_exc()
    logger.error(f"UNHANDLED EXCEPTION in {request.method} {request.url.path}:")
    logger.error(f"   Error: {str(exc)}")
    logger.error(f"   Type: {type(exc).__name__}")
    logger.error(f"   Traceback:\n{error_traceback}")
    
    return Response(
        status_code=500,
        content='{"detail": "Internal server error. Please try again."}',
        media_type="application/json"
    )


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
    logger.warning("OAuth routes not available (authlib may not be installed)")

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
    
    @app.get("/api/recommendations/secret-spots")
    async def secret_spots_fallback(
        limit: int = Query(default=2, ge=1, le=5),
        current_user: dict = Depends(get_current_user),
    ):
        """Get secret spots - unique profile-based recommendations"""
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
    # Health checks
    health_status = {
        "status": "healthy",
        "service": "bacolod-tourist-api",
        "bigquery": bigquery_client._is_available() if bigquery_client else False,
        "cloud_storage": storage_client._is_available() if storage_client else False,
        "redis": redis_client.is_connected() if redis_client else False
    }
    return health_status

