# Bacolod Tourist AI Web App

An AI-powered web application tailored for tourists visiting Bacolod, Philippines. The app offers personalized destination recommendations, hidden gems, and activities based on user personality profiles inferred from interactions.

## Tech Stack

### Frontend
- **Next.js 14** (App Router) with TypeScript
- **TailwindCSS** for styling
- **Google Maps** for interactive mapping

### Backend
- **FastAPI** for REST API
- **LangChain** for LLM orchestration
- **LangGraph** for multi-step conversational flows
- **FAISS** for vector similarity search
- **MongoDB** for user profiles and data
- **Redis** for caching and session management

## Getting Started

### Prerequisites
- Node.js >= 18
- pnpm >= 9
- Python >= 3.11
- Poetry (for Python dependency management)
- Docker and Docker Compose (for MongoDB and Redis)

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd Bacolod_Tourist
```

2. Install root dependencies:
```bash
pnpm install
```

3. Set up backend:
```bash
cd backend
poetry install
cp .env.example .env  # Create and configure your .env file
cd ..
```

4. Start infrastructure services:
```bash
docker-compose up -d
```

5. Run development servers:
```bash
# From root directory
pnpm dev
```

This will start:
- Frontend on http://localhost:3000
- Backend on http://localhost:8000

## Project Structure

```
.
├── frontend/          # Next.js application
│   ├── src/
│   │   └── app/      # App Router pages
│   └── ...
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── auth.py
│   │   ├── user_profile.py
│   │   ├── recommendation.py
│   │   ├── rag_engine.py
│   │   ├── langgraph_flow.py
│   │   ├── chat_agent.py
│   │   └── mcp_core.py
│   └── ...
├── docker-compose.yml
└── plan.md          # Development plan and roadmap
```

## Testing

```bash
# Frontend tests
pnpm --filter frontend test

# Backend tests
pnpm --filter backend test

# All tests
pnpm test
```

## Development Plan

See [plan.md](./plan.md) for the detailed phase-by-phase development roadmap.

## License

MIT

