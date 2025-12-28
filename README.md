# Inasal AI Web App

An intelligent, AI-powered tourism platform designed specifically for visitors to Bacolod, Philippines. Inasal leverages advanced AI technology to provide personalized travel recommendations, discover hidden gems, and curate unique experiences tailored to each user's personality profile. The platform uses machine learning to understand user preferences through interactions and continuously adapts recommendations to match individual travel styles.

## 🌟 Key Features

- **AI-Powered Chat Assistant**: Interactive chat interface powered by Anthropic Claude for real-time travel advice
- **Personalized Recommendations**: Smart destination suggestions based on personality inference and behavior tracking
- **Hidden Gems Discovery**: Uncover off-the-beaten-path attractions and local favorites
- **Personality-Based Matching**: Advanced personality profiling system that learns from user interactions
- **Real-Time Data Integration**: Weather, events, and news updates for informed travel planning
- **Social Profile Analysis**: Optional OAuth integration (Facebook, Twitter, LinkedIn) for enhanced personalization
- **Interactive Maps**: Google Maps integration for location-based exploration

## 🏗️ Architecture Overview

Inasal uses a modern hybrid architecture that combines the best of custom backend logic, headless CMS, and AI automation:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│              Next.js 16 (React + TypeScript)                │
│              - User Interface & Interactions                 │
│              - Real-time Chat Interface                     │
│              - Interactive Maps & Dashboards                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Orchestration Layer               │
│              - API Gateway & Request Routing                 │
│              - Authentication & Authorization                 │
│              - Business Logic & Data Processing             │
│              - Session Management & Caching                 │
└───────────────┬───────────────────────┬───────────────────┘
                │                       │
                ▼                       ▼
    ┌───────────────────┐   ┌──────────────────────┐
    │   Strapi CMS      │   │   Make.com AI         │
    │   (Content Layer) │   │   (Automation Layer)  │
    │                   │   │                       │
    │ - User Profiles   │   │ - AI Chat Workflows   │
    │ - Attractions Data │   │ - Recommendation Gen  │
    │ - Interaction Logs │   │ - Personality Analysis│
    │ - Recommendations  │   │ - External API Calls  │
    └───────────────────┘   └──────────────────────┘
                │                       │
                └───────────┬───────────┘
                            ▼
            ┌───────────────────────────────┐
            │      Data Storage Layer       │
            │                               │
            │  MongoDB Atlas (User Data)    │
            │  Redis Cloud (Caching)        │
            │  FAISS (Vector Search)        │
            └───────────────────────────────┘
```

## 🔗 Integration Architecture

### How Strapi CMS is Connected

**Strapi** serves as the content management backbone, storing and managing all structured data:

1. **Connection Method**: FastAPI backend communicates with Strapi via REST API using HTTP requests
2. **Authentication**: Bearer token authentication using API tokens generated in Strapi admin panel
3. **Data Flow**:
   - Frontend requests → FastAPI routes → `StrapiClient` → Strapi REST API → Response
   - All content operations (CRUD) for attractions, user profiles, and interaction logs go through Strapi
4. **Key Components**:
   - `StrapiClient` class (`backend/app/strapi_client.py`) handles all Strapi API interactions
   - Content types: User Profiles, Attractions, Interaction Logs, Recommendations
   - Admin panel for non-technical content management

**Example Flow:**
```python
# Backend route receives request
@router.get("/api/attractions")
async def get_attractions():
    # FastAPI calls StrapiClient
    attractions = await strapi_client.get_attractions()
    return attractions
```

### How Make.com AI Automation is Connected

**Make.com** handles all AI-powered workflows and external integrations:

1. **Connection Method**: Webhook-based HTTP POST requests from FastAPI to Make.com webhooks
2. **Workflow Types**:
   - **Chat Workflow**: Processes user messages, calls Anthropic Claude API, returns AI responses
   - **Recommendations Workflow**: Generates personalized recommendations based on user profile
   - **Persona Discovery Workflow**: Analyzes user interactions to infer personality traits
3. **Data Flow**:
   - Frontend → FastAPI → `MakeClient` → Make.com Webhook → AI Processing → Response
   - Make.com workflows can call external APIs (weather, events, news) and AI services
4. **Key Components**:
   - `MakeClient` class (`backend/app/make_client.py`) handles webhook calls
   - Three webhook endpoints configured in environment variables
   - Fallback to local LangChain implementation if Make.com unavailable

**Example Flow:**
```python
# User sends chat message
@router.post("/api/chat")
async def chat(message: ChatMessage):
    # FastAPI calls Make.com webhook
    response = await make_client.send_chat_message(
        user_id, message.text
    )
    # Make.com workflow:
    # 1. Receives message
    # 2. Calls Anthropic Claude API
    # 3. Processes response
    # 4. Returns AI-generated reply
    return response
```

### Integration Benefits

- **Separation of Concerns**: Content management (Strapi) vs. AI automation (Make.com) vs. Business logic (FastAPI)
- **Scalability**: Each service can scale independently
- **Flexibility**: Easy to modify AI workflows in Make.com without code changes
- **Maintainability**: Non-technical users can manage content via Strapi admin panel
- **Reliability**: Fallback mechanisms ensure service continues even if one component fails

## 🛠️ Tech Stack

### Frontend
- **Next.js 16** (App Router) with TypeScript
- **TailwindCSS 4** for modern, responsive styling
- **Google Maps API** for interactive mapping
- **Vitest** for unit testing
- **Playwright** for end-to-end testing

### Backend Architecture (Hybrid Approach)

**FastAPI** (Orchestration & Business Logic)
- REST API gateway and request routing
- Authentication & authorization (JWT-based)
- Custom business logic and calculations
- Session management with Redis
- Rate limiting and security middleware
- CORS configuration with environment-based origins

**Strapi CMS** (Content Management)
- Headless CMS for structured content
- User profiles and personality data storage
- Attractions database with rich metadata
- Interaction logs and analytics
- REST API for content operations
- Admin panel for content editors

**Make.com** (AI Automation & Workflows)
- AI chat workflows with Anthropic Claude integration
- Personalized recommendation generation
- Personality inference automation
- External API integrations (weather, events, news)
- Scheduled tasks and data synchronization
- Webhook-based event processing

### Infrastructure
- **MongoDB Atlas**: User data and session storage (legacy, migrating to Strapi)
- **Redis Cloud**: Caching and session management
- **FAISS**: Vector similarity search for recommendations (legacy)
- **Docker**: Containerization for local development
- **Railway**: Backend and Strapi hosting
- **Vercel**: Frontend hosting with Next.js optimization

## 🚀 Recent Updates & Deployment

### Deployment Infrastructure

The application now supports **staging and production environments** with automated deployments:

- **Staging Environment**: Test changes safely before production
  - Branch: `staging`
  - URLs: `staging-backend.railway.app`, `staging-strapi.railway.app`, `staging-app.vercel.app`
  
- **Production Environment**: Live application for end users
  - Branch: `main`
  - URLs: `production-backend.railway.app`, `production-strapi.railway.app`, `production-app.vercel.app`

### Configuration Files Added

- `backend/Dockerfile` - Container configuration for backend deployment
- `backend/railway.json` - Railway deployment configuration
- `strapi-backend/Dockerfile` - Container configuration for Strapi
- `strapi-backend/railway.json` - Railway deployment configuration
- `frontend/vercel.json` - Vercel deployment configuration

### Code Improvements

- **CORS Configuration**: Updated to use environment variables (`ALLOWED_ORIGINS`) for flexible origin management
- **Environment-Based Settings**: Production and staging use separate configurations
- **Deployment Documentation**: Comprehensive guides for Railway, Vercel, MongoDB Atlas, and Redis Cloud

See [DEPLOYMENT_GUIDE.html](./DEPLOYMENT_GUIDE.html) for complete deployment instructions.

## 📦 Getting Started

### Prerequisites
- Node.js >= 18
- pnpm >= 9
- Python >= 3.11
- Poetry (for Python dependency management)
- Docker and Docker Compose (for MongoDB and Redis)
- Make.com account (free tier available)
- Anthropic API key

### Installation

1. **Clone the repository:**
```bash
git clone <repo-url>
cd Inasal
```

2. **Install root dependencies:**
```bash
pnpm install
```

3. **Set up backend:**
```bash
cd backend
poetry install
cp .env.example .env  # Create and configure your .env file
cd ..
```

4. **Set up Strapi:**
```bash
cd strapi-backend
npm install
npm run develop
# Create admin account and API token in admin panel
cd ..
```

5. **Configure environment variables:**
```env
# Backend .env
STRAPI_URL=http://localhost:1337
STRAPI_API_TOKEN=your_strapi_token
MAKE_WEBHOOK_CHAT=https://hook.make.com/your-chat-webhook
MAKE_WEBHOOK_RECOMMENDATIONS=https://hook.make.com/your-recommendations-webhook
MAKE_WEBHOOK_PERSONA=https://hook.make.com/your-persona-webhook
ANTHROPIC_API_KEY=your_anthropic_key
```

6. **Start infrastructure services:**
```bash
docker-compose up -d
```

7. **Run development servers:**
```bash
# From root directory
pnpm dev
```

This will start:
- Frontend on http://localhost:3000
- Backend on http://localhost:8000
- Strapi on http://localhost:1337

## 📁 Project Structure

```
.
├── frontend/              # Next.js application
│   ├── src/
│   │   ├── app/          # App Router pages
│   │   │   ├── login/    # Authentication pages
│   │   │   ├── dashboard/# Main dashboard
│   │   │   ├── chat/     # AI chat interface
│   │   │   └── map/      # Interactive maps
│   │   └── lib/          # API clients and utilities
│   │       ├── api.ts    # FastAPI client
│   │       └── analytics.ts
│   └── ...
├── backend/              # FastAPI application (orchestration layer)
│   ├── app/
│   │   ├── auth.py       # Authentication logic
│   │   ├── strapi_client.py    # Strapi API client
│   │   ├── make_client.py      # Make.com webhook client
│   │   ├── routes/        # API routes
│   │   │   ├── auth_routes.py
│   │   │   ├── chat_routes.py
│   │   │   ├── recommendation_routes.py
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── strapi-backend/        # Strapi CMS
│   ├── src/
│   │   ├── api/          # Content types
│   │   │   ├── user-profile/
│   │   │   ├── attraction/
│   │   │   ├── interaction-log/
│   │   │   └── recommendation/
│   │   └── ...
│   └── ...
├── docker-compose.yml     # Local development services
├── DEPLOYMENT_GUIDE.html # Complete deployment guide
└── README.md             # This file
```

## 🧪 Testing

```bash
# Frontend tests
pnpm --filter frontend test

# Backend tests
pnpm --filter backend test

# All tests
pnpm test

# E2E tests
pnpm --filter frontend test:e2e
```

## 🔄 Development Workflow

### Branch Strategy

- **`main`**: Production branch (auto-deploys to production)
- **`staging`**: Staging branch (auto-deploys to staging environment)

### Typical Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-feature

# 2. Make changes and commit
git add .
git commit -m "Add new feature"

# 3. Push to staging for testing
git checkout staging
git merge feature/new-feature
git push origin staging

# 4. Test on staging environment
# Visit: https://staging-app.vercel.app

# 5. Deploy to production
git checkout main
git merge staging
git push origin main
```

## 📚 Documentation

- **[DEPLOYMENT_GUIDE.html](./DEPLOYMENT_GUIDE.html)** - Complete deployment guide for Railway, Vercel, MongoDB Atlas, and Redis Cloud
- **[STRAPI_SETUP_GUIDE.md](./STRAPI_SETUP_GUIDE.md)** - Detailed Strapi CMS setup instructions
- **[FLOW_EXPLANATION.md](./FLOW_EXPLANATION.md)** - Architecture and data flow documentation
- **[SETUP_INSTRUCTIONS.md](./SETUP_INSTRUCTIONS.md)** - Quick setup guide

## 🔐 Environment Variables

### Backend Required Variables

```env
# Database
DATABASE_URL=mongodb+srv://...
REDIS_URL=rediss://...

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Strapi Integration
STRAPI_URL=http://localhost:1337
STRAPI_API_TOKEN=your_strapi_token

# Make.com Integration
MAKE_WEBHOOK_CHAT=https://hook.make.com/your-chat-webhook
MAKE_WEBHOOK_RECOMMENDATIONS=https://hook.make.com/your-recommendations-webhook
MAKE_WEBHOOK_PERSONA=https://hook.make.com/your-persona-webhook

# AI Services
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-haiku-20240307

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
```

### Frontend Required Variables

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRAPI_URL=http://localhost:1337
```

## 🚢 Deployment

The application is configured for deployment on:

- **Railway**: Backend (FastAPI) and Strapi CMS
- **Vercel**: Frontend (Next.js)
- **MongoDB Atlas**: Database hosting
- **Redis Cloud**: Cache and session storage

See [DEPLOYMENT_GUIDE.html](./DEPLOYMENT_GUIDE.html) for step-by-step deployment instructions.

## 🤝 Contributing

1. Create a feature branch from `staging`
2. Make your changes
3. Test thoroughly
4. Submit a pull request to `staging` branch

## 📄 License

MIT

---

**Built with ❤️ for Bacolod, Philippines**
