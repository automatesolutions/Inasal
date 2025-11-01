# Bacolod Tourist Backend

FastAPI backend with LangChain, LangGraph, and AI-powered recommendation engine.

## Setup

1. Install Poetry: `pip install poetry` or `curl -sSL https://install.python-poetry.org | python3 -`
2. Install dependencies: `poetry install`
3. Activate virtual environment: `poetry shell`
4. Run development server: `pnpm dev` (from root) or `poetry run uvicorn app.main:app --reload`

## Environment Variables

Create a `.env` file in the backend directory:

```env
DATABASE_URL=mongodb://localhost:27017/bacolod_tourist
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=your_openai_api_key
JWT_SECRET_KEY=your_jwt_secret
JWT_ALGORITHM=HS256
```

