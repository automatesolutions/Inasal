"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth_routes, chat_routes

app = FastAPI(
    title="Bacolod Tourist API",
    description="AI-powered tourism API for Bacolod, Philippines",
    version="0.1.0",
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


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Bacolod Tourist API", "status": "healthy"}


@app.get("/health")
async def health():
    """Detailed health check"""
    return {"status": "healthy", "service": "bacolod-tourist-api"}

