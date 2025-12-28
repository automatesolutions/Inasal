## Bacolod Tourist AI Web App Plan

### Vision
- [ ] Deliver an AI-powered travel companion that greets Bacolod tourists with culturally rich UI, hyper-personalized itineraries, and responsive assistance across web and mobile form factors.

### Guiding Principles
- [ ] Prioritize iterative delivery: ship thin vertical slices per iteration, validate with real content, and refine via feedback.
- [ ] Uphold responsible AI: transparent recommendations, guardrails for hallucinations, and clear opt-in for data use.
- [ ] Enforce quality: unit tests for business logic, e2e tests for core journeys, automated checks in CI/CD.
- [ ] Embrace infrastructure-as-code and reproducible environments (Docker, pnpm, FastAPI, LangChain stack).
- [ ] **Hybrid Architecture**: Leverage best-of-breed solutions - FastAPI for business logic, Strapi for content, Make.com for AI automation.

### Architecture Overview (Hybrid Approach)

**FastAPI Backend** (Custom Business Logic)
- Custom business logic and calculations
- Real-time features (WebSockets, SSE)
- Complex data processing
- Rate limiting and security middleware
- API orchestration layer

**Strapi CMS** (Content Management)
- User profiles and authentication
- Attractions data (CRUD operations)
- Content management (images, descriptions, metadata)
- REST/GraphQL APIs for content
- Admin panel for non-technical users

**Make.com** (AI Workflows & Automation)
- AI chat workflows (OpenAI/Anthropic integration)
- Recommendation generation workflows
- Personality inference automation
- External API integrations (weather, events, news)
- Scheduled tasks (data sync, cleanup)
- Webhook-based event processing

### Phase Roadmap

#### Phase 0 — Project Foundation (Estimated: Week 0-1)
- [x] Confirm product scope, success metrics, and primary user personas (solo traveler, foodie, culture-seeker).
- [x] Decide on LLM provider (OpenAI, Anthropic, etc.) and quota strategy.
- [x] Bootstrap mono-repo with pnpm workspace (Next.js frontend, FastAPI backend) and shared packages directory.
- [x] Configure dev tooling: linting, formatting, pre-commit hooks, git branch strategy, descriptive commit template.
- [x] Set up Docker multi-stage builds and base GitHub Actions CI skeleton (lint + tests).

#### Phase 1 — Authentication & Cultural UI Shell (Estimated: Week 1-2)
- [x] Implement email-based login (magic link / OTP) via `auth.py` and integrate with NextAuth or custom flow.
- [x] Style `LoginPage` with animated Bacolod-themed background (Festival of Smiles palette, mask motifs, sugarcane gradients).
- [x] Scaffold `Dashboard`, `ChatAssistant`, and `MapView` routes with placeholder data using Tailwind.
- [x] Stub FastAPI endpoints for auth and health checks; return mock data to unblock frontend.
- [x] Connect frontend login to backend API endpoints (`/api/auth/send-otp`, `/api/auth/verify-otp`).
- [x] Establish Playwright (or Cypress) e2e smoke test covering login journey (5 tests passing).

#### Phase 2 — User Profile & Persistence Layer (Estimated: Week 2-3)
- [x] Model MongoDB collections for users, preferences, interaction logs; add Pydantic schemas.
- [x] Implement `user_profile.py` CRUD APIs, integrate JWT session management between frontend and backend.
- [x] Stand up Redis (local + Docker) for session caching and chat memory stub.
- [x] Integrate AWS Secrets Manager client for storing credentials (OAuth, DB URI, LLM keys).
- [x] Add backend unit tests for auth and profile modules (12 tests passing); extend e2e test for dashboard rendering personalized stub.

#### Phase 3 — Recommendation Engine & Vector Store (Estimated: Week 3-4)
- [x] Curate initial Bacolod attractions dataset; embed using chosen LLM embeddings model.
- [x] Set up FAISS (local) with option to swap to Pinecone in production; expose ingestion pipeline scripts.
- [x] Implement `recommendation.py` using LangChain chains to combine personality profile + vector search results.
- [x] Introduce prompt templates and configuration management for experimentation.
- [x] Write unit tests for recommendation scoring logic and retrieval adapters.

#### Phase 4 — RAG Engine & Real-Time Enrichment (Estimated: Week 4-5)
- [x] Implement `rag_engine.py` to orchestrate weather, events, and local news sources (RSS/API) with caching strategy.
- [x] Compose Retrieval-Augmented prompts that blend live data with vector hits.
- [x] Add monitoring hooks (structured logging, fallback flows when external data unavailable).
- [x] Extend e2e tests to validate itinerary updates when external data changes (mock APIs).
- [x] Define evaluation script for LLM responses (quality + safety heuristics).

#### Phase 5 — LangGraph Flows & Itinerary Builder (Estimated: Week 5-6)
- [ ] Design LangGraph workflow for multi-day itinerary planning with branching nodes (explore, refine, confirm).
- [ ] Build `ItineraryBuilder` UI with stepper experience and progress state synced to backend graph state.
- [ ] Persist itinerary revisions and personality traits back to MongoDB.
- [ ] Add unit tests for LangGraph nodes and workflow transitions.
- [ ] Create integration tests validating end-to-end itinerary generation path.

#### Phase 6 — Chat Assistant & Map Experience (Estimated: Week 6-7)
- [x] Implement `chat_agent.py` leveraging LangChain ConversationChain + memory modules.
- [ ] Connect Chat UI to backend streaming endpoint (Server-Sent Events or WebSocket).
- [ ] Embed Mapbox (or Google Maps) in `MapView` with AI-curated pins and cluster styling.
- [ ] Synchronize chat suggestions with map highlights and dashboard cards.
- [ ] Extend Playwright e2e to cover chat interaction + map update validation.

#### Phase 7 — Production Hardening & Observability (Estimated: Week 7-8)
- [ ] Harden security (rate limiting, JWT rotation, secrets rotation workflows).
- [ ] Implement GitHub Actions CI/CD (build, test, docker push, deploy trigger to ECS/EC2).
- [ ] Configure CloudWatch dashboards and Prometheus scraping (container metrics, latency, LLM usage).
- [ ] Load/performance profiling, cost monitoring, and caching optimizations.
- [ ] Draft launch playbook and rollback procedures.

#### Phase 8 — OAuth Integration & Automatic Personality Inference (Estimated: Week 8-10)
- [x] OAuth authentication setup (Facebook, Twitter, LinkedIn)
- [x] Social profile data extraction and parsing
- [x] LLM-based personality inference from social media profiles
- [x] **Email-based personality inference** (Internet search from email patterns)
- [x] Automatic recommendation generation on login
- [x] Behavior tracking system for user interactions
- [x] Adaptive personality updates based on browsing behavior
- [x] Dashboard auto-loads recommendations (no click required)
- [x] Analytics API for tracking interactions
- [x] Frontend OAuth login buttons and callback handler
- [x] **Free LLM Integration (Ollama)** - No more quota issues!
- [x] **Chain Prompt Engineering** - Modular 3-step recommendation process
- [x] **Web Scraping Module** - Ready for hotels, adventures, events

#### Phase 9 — Hybrid Architecture Migration: Strapi + Make.com Integration (Estimated: Week 10-14)

**Phase 9.1 — Strapi Setup & Content Migration (Week 10-11)**
- [ ] Install and configure Strapi (local development + production setup)
- [ ] Create Strapi content types:
  - [ ] **User Profile** (user_id, email, name, personality JSON, preferences JSON, travel_history JSON)
  - [ ] **Attraction** (name, type, description, location component, tags, images, personality_match JSON)
  - [ ] **Interaction Log** (user_id relation, interaction_type, content JSON, metadata JSON, timestamp)
  - [ ] **Recommendation** (user_id relation, hotels JSON, restaurants JSON, entertainment JSON, tourist_spots JSON, secret_recommendations JSON)
- [ ] Configure Strapi authentication (JWT, API tokens, permissions)
- [ ] Set up Strapi custom API endpoints for OTP flow (`/api/auth/send-otp`, `/api/auth/verify-otp`)
- [ ] Migrate attractions data from MongoDB/JSON to Strapi
- [ ] Create migration script for user profiles (MongoDB → Strapi)
- [ ] Set up Strapi webhooks for content updates
- [ ] Configure Strapi media library for images
- [ ] Test Strapi API endpoints (REST and GraphQL)

**Phase 9.2 — Make.com Workflow Setup (Week 11-12)**
- [ ] Create Make.com account and workspace
- [ ] Set up **Chat Workflow**:
  - [ ] Webhook trigger (receives chat message from frontend)
  - [ ] HTTP request to OpenAI/Anthropic API (chat completion)
  - [ ] HTTP request to Strapi (create interaction log)
  - [ ] HTTP request to Strapi (update user profile if needed)
  - [ ] Return response to frontend webhook
  - [ ] Error handling and retry logic
- [ ] Set up **Recommendation Workflow**:
  - [ ] Webhook trigger (user requests recommendations)
  - [ ] HTTP request to Strapi (get user profile)
  - [ ] HTTP request to OpenAI/Anthropic (generate recommendations based on profile)
  - [ ] HTTP request to Strapi (get attractions data)
  - [ ] Data processing module (match recommendations with attractions)
  - [ ] HTTP request to Strapi (save recommendations)
  - [ ] Return recommendations to frontend webhook
- [ ] Set up **Persona Discovery Workflow**:
  - [ ] Webhook trigger (new user signup or profile update)
  - [ ] HTTP request to Strapi (get user data)
  - [ ] HTTP request to OpenAI/Anthropic (analyze personality from social data)
  - [ ] HTTP request to Strapi (update user profile with personality traits)
  - [ ] Trigger recommendation generation workflow
- [ ] Set up **Scheduled Tasks**:
  - [ ] Daily attraction data sync (scrape and update Strapi)
  - [ ] Weekly user profile cleanup (inactive users)
  - [ ] Periodic recommendation cache refresh
- [ ] Configure Make.com webhook authentication (API keys, tokens)
- [ ] Test all Make.com scenarios end-to-end
- [ ] Set up Make.com error notifications (email/Slack)

**Phase 9.3 — FastAPI Refactoring (Week 12-13)**
- [ ] Refactor FastAPI to act as orchestration layer:
  - [ ] Keep custom business logic endpoints
  - [ ] Keep real-time features (WebSocket chat, SSE streaming)
  - [ ] Keep complex calculations (recommendation scoring algorithms)
  - [ ] Keep rate limiting and security middleware
- [ ] Update FastAPI to proxy Strapi APIs:
  - [ ] `/api/profile/*` → Proxy to Strapi with authentication
  - [ ] `/api/attractions/*` → Proxy to Strapi
  - [ ] `/api/interactions/*` → Proxy to Strapi
- [ ] Update FastAPI to call Make.com webhooks:
  - [ ] `/api/chat` → Call Make.com chat webhook
  - [ ] `/api/recommendations` → Call Make.com recommendation webhook
  - [ ] `/api/persona-discovery` → Call Make.com persona webhook
- [ ] Remove LangChain dependencies from FastAPI (migrate to Make.com)
- [ ] Keep Redis for caching and session management
- [ ] Update FastAPI tests to mock Strapi and Make.com calls
- [ ] Document API architecture (FastAPI → Strapi → Make.com flow)

**Phase 9.4 — Frontend Integration (Week 13-14)**
- [ ] Update frontend API client (`src/lib/api.ts`):
  - [ ] Add Strapi base URL configuration
  - [ ] Add Make.com webhook URLs configuration
  - [ ] Update authentication flow (Strapi JWT tokens)
  - [ ] Update profile API calls (Strapi endpoints)
  - [ ] Update attractions API calls (Strapi endpoints)
  - [ ] Update chat API calls (Make.com webhooks via FastAPI proxy)
  - [ ] Update recommendations API calls (Make.com webhooks via FastAPI proxy)
- [ ] Update environment variables:
  - [ ] `NEXT_PUBLIC_STRAPI_URL`
  - [ ] `NEXT_PUBLIC_STRAPI_API_TOKEN`
  - [ ] `NEXT_PUBLIC_MAKE_WEBHOOK_CHAT`
  - [ ] `NEXT_PUBLIC_MAKE_WEBHOOK_RECOMMENDATIONS`
  - [ ] `NEXT_PUBLIC_MAKE_WEBHOOK_PERSONA`
- [ ] Update frontend tests to mock Strapi and Make.com responses
- [ ] Test end-to-end user flows (login → profile → chat → recommendations)
- [ ] Update frontend error handling for Strapi/Make.com errors

**Phase 9.5 — Data Migration & Testing (Week 14)**
- [ ] Create comprehensive migration script:
  - [ ] Migrate user profiles (MongoDB → Strapi)
  - [ ] Migrate interaction logs (MongoDB → Strapi)
  - [ ] Migrate attractions (JSON → Strapi)
  - [ ] Verify data integrity
- [ ] Run migration in staging environment
- [ ] Test all user journeys in staging
- [ ] Performance testing (Strapi API response times, Make.com webhook latency)
- [ ] Load testing (concurrent users, webhook throughput)
- [ ] Rollback plan documentation
- [ ] Production migration execution
- [ ] Post-migration monitoring and validation

### Cross-Cutting Workstreams
- [ ] UX Research & Content: continual refinement of Bacolod storytelling, imagery, and copy.
- [ ] Prompt Engineering: maintain prompt library, track experiments, version control prompt changes.
- [ ] Data Governance: define data retention, anonymization of interaction logs, consent flows.
- [ ] Documentation: keep `plan.md`, architecture diagrams, and onboarding guides up to date.

### Testing Strategy
- [x] Backend: pytest for unit/integration; coverage thresholds set early (12 tests passing).
- [x] Frontend: Vitest/RTL for components; Playwright for e2e core journeys (19 component tests + 5 e2e tests passing).
- [ ] AI Evaluation: offline replay tests, prompt regression suites, human-in-the-loop review cadence.

### Tooling & DevEx Checklist
- [x] pnpm workspace root scripts (`dev`, `build`, `test`, `lint`) smoothing DX.
- [ ] VSCode/Editor configs (tailwind intellisense, Python formatting) shared.
- [x] Docker Compose for local stack (Next.js, FastAPI, MongoDB, Redis, FAISS service).
- [ ] Seed scripts for sample users and attraction data to ease onboarding.

### Key Decisions (Confirmed)
- [x] LLM provider priority: optimize for cost-effective model tiers.
- [x] Email login flow: in-house OTP implementation.
- [x] Map provider: Google Maps integration.
- [x] Chatbot tone: friendly local guide persona.
- [ ] Source of real-time events/weather feeds (official tourism board, third-party APIs).
- [x] **Architecture**: Hybrid approach - FastAPI (business logic), Strapi (content), Make.com (AI workflows).
- [x] **Content Management**: Strapi for attractions, user profiles, and content CRUD operations.
- [x] **AI Automation**: Make.com for LLM workflows, external integrations, and scheduled tasks.

### Phase Completion Status
- ✅ **Phase 0** - Project Foundation: COMPLETE
- ✅ **Phase 1** - Authentication & Cultural UI Shell: COMPLETE (frontend connected to backend, e2e tests passing)
- ✅ **Phase 2** - User Profile & Persistence Layer: COMPLETE
- ✅ **Phase 3** - Recommendation Engine & Vector Store: COMPLETE
- ✅ **Phase 4** - RAG Engine & Real-Time Enrichment: COMPLETE
- ⏸️ **Phase 5** - LangGraph Flows & Itinerary Builder: PENDING (will be replaced by Make.com workflows)
- 🔄 **Phase 6** - Chat Assistant & Map Experience: PARTIALLY COMPLETE (chat agent done, frontend chat UI done, map pending)
- ⏸️ **Phase 7** - Production Hardening & Observability: PENDING
- ✅ **Phase 8** - OAuth Integration & Automatic Personality Inference: COMPLETE
- 🆕 **Phase 9** - Hybrid Architecture Migration: Strapi + Make.com Integration: NOT STARTED

### Progress Summary
**Completed:**
- Project foundation (monorepo, tooling, CI/CD setup)
- Authentication system with OTP and JWT
- **Frontend connected to backend API** (login flow fully functional)
- UI shell with Login, Dashboard, Chat, and Map pages
- MongoDB integration with full user profile CRUD
- Redis integration for sessions and chat memory
- Chat agent with LangChain and conversation memory
- **Email sending implementation** (SMTP with console fallback for dev)
- **Comprehensive testing infrastructure:**
  - Backend: 12 unit tests passing (auth, user profiles)
  - Frontend: 19 component tests passing (Login, Dashboard, Chat, Home pages)
  - Frontend: 5 e2e tests passing (login journey, navigation)
  - Total: **36 tests passing**
- Core functionality test suite with graceful LangChain fallback
- Recommendation engine with FAISS vector store
- Bacolod attractions dataset (12 attractions)
- Personality-based recommendation scoring
- Prompt templates for AI interactions
- Data ingestion pipeline
- RAG engine with weather, events, and news integration
- Redis caching for real-time data
- Recommendation enrichment with live context
- LLM response evaluation system
- Server can start without LangChain dependencies (graceful degradation)
- **OAuth integration (Facebook, Twitter, LinkedIn)**
- **Social profile data extraction and parsing**
- **LLM-based personality inference from social media profiles**
- **Automatic recommendation generation on login (cached in Redis)**
- **Behavior tracking system (analytics API)**
- **Adaptive personality updates based on user interactions**
- **Dashboard auto-loads recommendations (no manual click needed)**

**In Progress:**
- LangGraph itinerary builder (will migrate to Make.com in Phase 9)

**Pending:**
- Google Maps integration
- Streaming chat endpoint (SSE/WebSocket) - chat UI ready, needs backend streaming
- Chat UI connected to backend API endpoint
- LangGraph itinerary builder UI (will use Make.com workflows instead)
- Production hardening (security, CI/CD, monitoring)
- **Phase 9 Migration**: Strapi setup, Make.com workflows, FastAPI refactoring, frontend integration

**Architecture Migration (Phase 9):**
- FastAPI will focus on: Custom business logic, complex calculations, real-time features (WebSockets/SSE)
- Strapi will handle: Content management, user profiles, attractions data, CRUD operations
- Make.com will handle: AI workflows (chat, recommendations, persona discovery), external integrations, scheduled tasks

> ✅ Phase progress is tracked in real-time. **Testing milestone complete: 36 tests passing (12 backend + 24 frontend)**. Frontend-backend integration for login is complete. 
> 
> **Next Major Focus: Phase 9 - Hybrid Architecture Migration**
> - Migrating to Strapi for content management (user profiles, attractions)
> - Migrating AI workflows to Make.com (chat, recommendations, persona discovery)
> - Refactoring FastAPI to focus on business logic and real-time features
> - This hybrid approach provides better separation of concerns, easier content management, and scalable AI automation

