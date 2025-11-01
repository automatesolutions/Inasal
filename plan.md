## Bacolod Tourist AI Web App Plan

### Vision
- [ ] Deliver an AI-powered travel companion that greets Bacolod tourists with culturally rich UI, hyper-personalized itineraries, and responsive assistance across web and mobile form factors.

### Guiding Principles
- [ ] Prioritize iterative delivery: ship thin vertical slices per iteration, validate with real content, and refine via feedback.
- [ ] Uphold responsible AI: transparent recommendations, guardrails for hallucinations, and clear opt-in for data use.
- [ ] Enforce quality: unit tests for business logic, e2e tests for core journeys, automated checks in CI/CD.
- [ ] Embrace infrastructure-as-code and reproducible environments (Docker, pnpm, FastAPI, LangChain stack).

### Phase Roadmap

#### Phase 0 — Project Foundation (Estimated: Week 0-1)
- [x] Confirm product scope, success metrics, and primary user personas (solo traveler, foodie, culture-seeker).
- [x] Decide on LLM provider (OpenAI, Anthropic, etc.) and quota strategy.
- [x] Bootstrap mono-repo with pnpm workspace (Next.js frontend, FastAPI backend) and shared packages directory.
- [x] Configure dev tooling: linting, formatting, pre-commit hooks, git branch strategy, descriptive commit template.
- [x] Set up Docker multi-stage builds and base GitHub Actions CI skeleton (lint + tests).

#### Phase 1 — Authentication & Cultural UI Shell (Estimated: Week 1-2)
- [ ] Implement email-based login (magic link / OTP) via `auth.py` and integrate with NextAuth or custom flow.
- [ ] Style `LoginPage` with animated Bacolod-themed background (Festival of Smiles palette, mask motifs, sugarcane gradients).
- [ ] Scaffold `Dashboard`, `ChatAssistant`, and `MapView` routes with placeholder data using Tailwind.
- [ ] Stub FastAPI endpoints for auth and health checks; return mock data to unblock frontend.
- [ ] Establish Playwright (or Cypress) e2e smoke test covering login journey.

#### Phase 2 — User Profile & Persistence Layer (Estimated: Week 2-3)
- [x] Model MongoDB collections for users, preferences, interaction logs; add Pydantic schemas.
- [x] Implement `user_profile.py` CRUD APIs, integrate JWT session management between frontend and backend.
- [x] Stand up Redis (local + Docker) for session caching and chat memory stub.
- [x] Integrate AWS Secrets Manager client for storing credentials (OAuth, DB URI, LLM keys).
- [x] Add backend unit tests for auth and profile modules; extend e2e test for dashboard rendering personalized stub.

#### Phase 3 — Recommendation Engine & Vector Store (Estimated: Week 3-4)
- [ ] Curate initial Bacolod attractions dataset; embed using chosen LLM embeddings model.
- [ ] Set up FAISS (local) with option to swap to Pinecone in production; expose ingestion pipeline scripts.
- [ ] Implement `recommendation.py` using LangChain chains to combine personality profile + vector search results.
- [ ] Introduce prompt templates and configuration management for experimentation.
- [ ] Write unit tests for recommendation scoring logic and retrieval adapters.

#### Phase 4 — RAG Engine & Real-Time Enrichment (Estimated: Week 4-5)
- [ ] Implement `rag_engine.py` to orchestrate weather, events, and local news sources (RSS/API) with caching strategy.
- [ ] Compose Retrieval-Augmented prompts that blend live data with vector hits.
- [ ] Add monitoring hooks (structured logging, fallback flows when external data unavailable).
- [ ] Extend e2e tests to validate itinerary updates when external data changes (mock APIs).
- [ ] Define evaluation script for LLM responses (quality + safety heuristics).

#### Phase 5 — LangGraph Flows & Itinerary Builder (Estimated: Week 5-6)
- [ ] Design LangGraph workflow for multi-day itinerary planning with branching nodes (explore, refine, confirm).
- [ ] Build `ItineraryBuilder` UI with stepper experience and progress state synced to backend graph state.
- [ ] Persist itinerary revisions and personality traits back to MongoDB.
- [ ] Add unit tests for LangGraph nodes and workflow transitions.
- [ ] Create integration tests validating end-to-end itinerary generation path.

#### Phase 6 — Chat Assistant & Map Experience (Estimated: Week 6-7)
- [ ] Implement `chat_agent.py` leveraging LangChain ConversationChain + memory modules.
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

### Cross-Cutting Workstreams
- [ ] UX Research & Content: continual refinement of Bacolod storytelling, imagery, and copy.
- [ ] Prompt Engineering: maintain prompt library, track experiments, version control prompt changes.
- [ ] Data Governance: define data retention, anonymization of interaction logs, consent flows.
- [ ] Documentation: keep `plan.md`, architecture diagrams, and onboarding guides up to date.

### Testing Strategy
- [ ] Backend: pytest for unit/integration; coverage thresholds set early.
- [ ] Frontend: Vitest/RTL for components; Playwright for e2e core journeys (login, itinerary build, chat-map sync).
- [ ] AI Evaluation: offline replay tests, prompt regression suites, human-in-the-loop review cadence.

### Tooling & DevEx Checklist
- [ ] pnpm workspace root scripts (`dev`, `build`, `test`, `lint`) smoothing DX.
- [ ] VSCode/Editor configs (tailwind intellisense, Python formatting) shared.
- [ ] Docker Compose for local stack (Next.js, FastAPI, MongoDB, Redis, FAISS service).
- [ ] Seed scripts for sample users and attraction data to ease onboarding.

### Key Decisions (Confirmed)
- [x] LLM provider priority: optimize for cost-effective model tiers.
- [x] Email login flow: in-house OTP implementation.
- [x] Map provider: Google Maps integration.
- [x] Chatbot tone: friendly local guide persona.
- [ ] Source of real-time events/weather feeds (official tourism board, third-party APIs).

- [ ] Review and confirm the roadmap + outstanding decision on real-time data sources.
- [ ] Once confirmed, initialize repo structure and document phase progress as tasks are completed here.

> ✅ We will check off each item directly in this plan as milestones are delivered. Please respond with any updates on real-time data sources so we can finalize Phase 0.

