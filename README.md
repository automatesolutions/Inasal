# Bacolod Tourist - MOGI Chatbot

An intelligent, AI-powered tourism platform designed specifically for visitors to Bacolod, Philippines. MOGI (M-O-G-I) is a friendly puppet mascot guide that leverages advanced AI technology to provide personalized travel recommendations, discover hidden gems, and curate unique experiences tailored to each user's personality profile.

## 🌟 Key Features

- **🎭 MOGI Chatbot**: Friendly puppy mascot guide powered by OpenAI GPT (or Make.com workflow) for personalized travel advice and recommendations
- **📱 Phone Number Authentication**: Philippine phone number-based login with OTP verification (supports both phone and email)
- **🤖 Automatic Personality Analysis**: Background social media scraping (Scrapy + Bright Data) and LLM-based personality inference; in-memory cache + BigQuery retry queue for instant personality display
- **🎯 Personality-Driven Recommendations**: Comprehensive recommendations (tourist spots, hotels, restaurants, beaches, mountains, resorts, events, businesses) via LangChain + FAISS; optional Make.com webhooks for hotels
  - **Smart Filtering**: Only shows specific places (not general articles/blog posts)
  - **No Duplicates**: Deduplication by normalized place names
  - **Quality Control**: Minimum 50% match score threshold
  - **Data Source**: All recommendations loaded directly from InstantDB scraped content (no static JSON)
- **💬 Interactive Chat Interface**: Chatbot-first experience with rich message formatting, clickable recommendation links, and personality-aware responses
- **🔐 Secret Spot Discovery**: Unique, profile-based secret spots (1-2 items) matched to hidden personality traits; dedicated `/secret-recommendations` page
- **⚠️ Safety First**: Comprehensive safety information with dedicated `/safety` page featuring:
  - Merged correlated scams and danger zones (no duplicates)
  - English translation for all content
  - Filtered to show only Bacolod-related information (excludes Manila, Sulu, Marawi, etc.)
  - Cleaned references (Tulfo → local police)
  - Malformed data filtering
- **📍 Precise Directions**: Every recommendation includes Google Maps links and precise navigation directions
- **💾 InstantDB Integration**: User profiles and recommendations saved to InstantDB (optional) for real-time retrieval; BigQuery primary for analytics
- **📊 Google Sheet Scraping**: Dynamic content scraping from Google Sheet with:
  - Category-based organization (Accommodation, Tourist Spots, Restaurants, Scams, Danger Zones, Secret Places)
  - Multi-entity extraction using LLM (extracts multiple hotels/restaurants from single articles)
  - Duplicate detection to avoid re-scraping
  - Bright Data Web Unlocker for JavaScript-heavy sites (Facebook, etc.)
  - Automatic linked website scraping (up to 3 links per page)
- **📊 Comprehensive Welcome Message**: Automatic personalized welcome with all recommendations in organized categories
- **🔄 Real-Time Data Integration**: Weather, events, and news (when APIs configured); RAG routes for contextual search
- **🗺️ Interactive Maps**: Google Maps integration for location-based exploration

## 🏗️ Architecture Overview

MOGI uses a modern architecture combining FastAPI backend, Next.js frontend, and AI-powered services:

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│              Next.js 16 (React + TypeScript + Tailwind)     │
│              - MOGI Chatbot Interface                        │
│              - Phone/Email Authentication                    │
│              - Recommendation Cards with Directions          │
│              - Secret Spot Badges (Profile-based)            │
│              - Safety Information Display                    │
│              - Interactive Maps & Dashboards                │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Orchestration Layer               │
│              - API Gateway & Request Routing                 │
│              - Phone/Email OTP Authentication                │
│              - MOGI Chatbot (Make.com or LangChain/OpenAI)    │
│              - Personality Analysis Pipeline                 │
│              - Social Media Scraping (Scrapy + Bright Data) │
│              - Comprehensive Recommendations Service         │
│              - Secret Spot Discovery (Profile-based)         │
│              - Scams & Danger Zones Safety Info              │
│              - InstantDB Recommendation Persistence          │
│              - Session Management & Caching                 │
└───────────────┬───────────────────────┬───────────────────┘
                │                       │
                ▼                       ▼
    ┌───────────────────┐   ┌──────────────────────┐
    │  Google BigQuery  │   │   Make.com AI         │
    │   (Database)      │   │   (Automation Layer)  │
    │                   │   │                       │
    │ - User Profiles   │   │ - AI Chat Workflows   │
    │ - Personality     │   │ - Recommendation Gen  │
    │ - Recommendation  │   │ - Personality Analysis│
    │   Scores          │   │ - External API Calls  │
    │ - Chat Logs       │   │                       │
    │ - Interaction Logs│   │                       │
    └───────────────────┘   └──────────────────────┘
                │                       │
                ▼                       │
    ┌───────────────────┐              │
    │ Google Cloud      │              │
    │ Storage (Files)   │              │
    │                   │              │
    │ - Images          │              │
    │ - Documents       │              │
    └───────────────────┘              │
                │                       │
                └───────────┬───────────┘
                            ▼
            ┌───────────────────────────────┐
            │      Data Storage Layer       │
            │                               │
            │  Google BigQuery (User Data)   │
            │  Google Cloud Storage (Files)  │
            │  Redis Cloud (Caching/OTP)    │
            │  FAISS (Vector Search)        │
            │  Bright Data (Social Scraping) │
            │  InstantDB (Real-time Recommendations) │
            └───────────────────────────────┘
```

## 🔗 Integration Architecture

### How Make.com AI Automation is Connected

**Make.com** handles all AI-powered workflows and external integrations:

1. **Connection Method**: Webhook-based HTTP POST requests from FastAPI to Make.com webhooks
2. **Workflow Types**:
   - **Chat Workflow**: Processes user messages, calls OpenAI GPT API, returns AI responses
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
    # 2. Calls OpenAI GPT API
    # 3. Processes response
    # 4. Returns AI-generated reply
    return response
```

### Social Media Scraping Architecture

**Scrapy + Bright Data Residential Proxy** handles automated social media profile scraping:

1. **Search Phase**: Uses Bright Data Google Search API to find Facebook/Instagram profiles
2. **Scraping Phase**: Uses Scrapy spiders with Bright Data Residential Proxy to extract profile data
3. **Data Flow**:
   - User Login → Background Job → Bright Data Search → Profile URLs Found
   - → Scrapy Spider (via Bright Data Proxy) → Profile Data Extracted
   - → LLM Analysis → Personality Traits → MongoDB Storage
4. **Key Components**:
   - `SocialMediaScraper` (`backend/app/social_scraper.py`) - Orchestrates search and scraping
   - `FacebookProfileSpider` / `InstagramProfileSpider` (`backend/app/scrapers/social_media_spider.py`) - Scrapy spiders
   - `BrightDataProxyMiddleware` (`backend/app/scrapers/proxy_middleware.py`) - Injects Bright Data proxy

## 🛠️ Tech Stack

### Frontend
- **Next.js 16** (App Router) with TypeScript
- **TailwindCSS 4** for modern, responsive styling
- **Google Maps API** for interactive mapping
- **Vitest** for unit testing
- **Playwright** for end-to-end testing

### Backend Architecture

**FastAPI** (Orchestration & Business Logic)
- REST API gateway and request routing
- Phone/Email OTP authentication (JWT-based)
- MOGI chatbot with personality-aware responses
- Background personality analysis pipeline
- Social media scraping integration (Scrapy + Bright Data Residential Proxy)
- Comprehensive recommendations service
- Session management with Redis
- Rate limiting and security middleware
- CORS configuration with environment-based origins

**Make.com** (AI Automation & Workflows) - Optional
- AI chat workflows with OpenAI GPT integration
- Personalized recommendation generation
- Personality inference automation
- External API integrations (weather, events, news)
- Scheduled tasks and data synchronization
- Webhook-based event processing

### Infrastructure
- **Google BigQuery**: User profiles, personality traits, recommendation scores, chat logs, and interaction history
- **Google Cloud Storage**: File and image storage
- **Redis Cloud**: Caching, OTP storage, and session management
- **FAISS**: Vector similarity search for recommendations
- **Bright Data**: Social media profile search and residential proxy for scraping
- **Docker**: Containerization for local development
- **Railway**: Backend hosting
- **Vercel**: Frontend hosting with Next.js optimization

## 🚀 Getting Started

### Prerequisites
- Node.js >= 18
- pnpm >= 9
- Python >= 3.11
- Poetry (for Python dependency management)
- Docker and Docker Compose (for Redis)
- Google Cloud Platform account (see [Google Cloud Setup](#-google-cloud-platform-setup) below)
- Make.com account (free tier available, optional)
- OpenAI API key (required for MOGI chatbot)
- Bright Data account (optional, for social media scraping)

## ☁️ Google Cloud Platform Setup

This application uses **Google BigQuery** for database storage and **Google Cloud Storage** for file storage. Follow these steps to set up your GCP environment:

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click **"New Project"**
4. Enter project name: `bacolod-tourist` (or your preferred name)
5. Note your **Project ID** (e.g., `gen-lang-client-0542256476`)
6. Click **"Create"**

### Step 2: Enable Required APIs

1. Go to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
2. Enable the following APIs:
   - **BigQuery API** - Search "BigQuery API" → Click → Enable
   - **Cloud Storage API** - Search "Cloud Storage API" → Click → Enable

### Step 3: Create a Service Account

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click **"Create Service Account"**
3. Enter details:
   - **Service account name**: `bacolod-tourist-service`
   - **Service account ID**: `bacolod-tourist-service` (auto-filled)
   - Click **"Create and Continue"**
4. Grant roles:
   - **BigQuery Admin** (or at minimum: BigQuery Data Editor, BigQuery Job User)
   - **Storage Admin** (or at minimum: Storage Object Admin)
   - Click **"Continue"** → **"Done"**

### Step 4: Create and Download Service Account Key

1. Click on the service account you just created
2. Go to **"Keys"** tab
3. Click **"Add Key"** → **"Create new key"**
4. Select **JSON** format
5. Click **"Create"** - This downloads a JSON file (e.g., `gen-lang-client-0542256476-399081ed3dc7.json`)
6. **Save this file** in your project: `backend/gen-lang-client-0542256476-399081ed3dc7.json`
   - ⚠️ **Important**: Add this file to `.gitignore` to keep credentials secure!

### Step 5: Create BigQuery Dataset

1. Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
2. In the left sidebar, click your **Project ID**
3. Click **"Create Dataset"** (or the **"⋮"** menu → **"Create dataset"**)
4. Enter details:
   - **Dataset ID**: `bacolod_tourist` (or `Inasal_app` if you prefer)
   - **Location type**: `Multi-region` → Select `US (multiple regions in United States)` or `Region` → Select `us-central1`
   - Click **"Create dataset"**
5. **Note your Dataset ID** - you'll need it for environment variables

**Note**: The application will automatically create the required tables (`user_profiles`, `interaction_logs`, `recommendation_scores`, `chat_logs`) on first connection.

### Step 6: Create Cloud Storage Bucket

1. Go to [Cloud Storage Console](https://console.cloud.google.com/storage/buckets)
2. Click **"Create Bucket"**
3. Enter details:
   - **Name**: `bacolod-tourist-storage` (must be globally unique)
   - **Location type**: `Multi-region` → Select `US (multiple regions in United States)` OR `Region` → Select `us-central1`
   - **Storage class**: `Standard`
   - **Access control**: `Uniform`
   - Click **"Create"**
4. **Note your Bucket Name** - you'll need it for environment variables

### Step 7: Configure Environment Variables

Update your `backend/.env` file with the GCP configuration:

```env
# Google Cloud Platform Configuration
GCP_PROJECT_ID=gen-lang-client-0542256476          # Your Project ID from Step 1
GCP_CREDENTIALS_PATH=backend/gen-lang-client-0542256476-399081ed3dc7.json  # Path to service account JSON
BIGQUERY_DATASET_ID=Inasal_app                     # Dataset ID from Step 5
GCS_BUCKET_NAME=inasal-app-storage                  # Bucket name from Step 6
GCS_BUCKET_LOCATION=us                              # Location: "us" for multi-region, "us-central1" for region
```

### Step 8: Verify Setup

1. **Test BigQuery Connection:**
   ```bash
   cd backend
   poetry shell
   poetry run python -c "from app.bigquery_client import bigquery_client; import asyncio; asyncio.run(bigquery_client.connect()); print('✅ BigQuery connected!')"
   ```

2. **Test Cloud Storage Connection:**
   ```bash
   poetry run python -c "from app.storage_client import storage_client; import asyncio; asyncio.run(storage_client.connect()); print('✅ Cloud Storage connected!')"
   ```

3. **Start the backend server:**
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```
   
   Check the console output - you should see:
   ```
   ✅ Connected to BigQuery: gen-lang-client-0542256476.Inasal_app
   ✅ Connected to Cloud Storage: inasal-app-storage
   ✅ Table user_profiles ready
   ✅ Table interaction_logs ready
   ✅ Table recommendation_scores ready
   ✅ Table chat_logs ready
   ```

### Troubleshooting

**Issue: "Permission denied" or "Access denied"**
- Verify service account has correct roles (BigQuery Admin, Storage Admin)
- Check that the JSON credentials file path is correct
- Ensure the service account email matches the one in your JSON file

**Issue: "Dataset not found"**
- Verify `BIGQUERY_DATASET_ID` matches the exact Dataset ID in BigQuery console
- Check that the dataset exists in the correct project

**Issue: "Bucket not found"**
- Verify `GCS_BUCKET_NAME` matches the exact bucket name (case-sensitive)
- Ensure the bucket exists in the correct project
- Check bucket permissions allow your service account access

**Issue: "Credentials file not found"**
- Verify `GCP_CREDENTIALS_PATH` is relative to the project root
- Check the file exists at the specified path
- Ensure the JSON file is valid (not corrupted)

### BigQuery Tables Created Automatically

The application automatically creates these tables on first connection:

1. **`user_profiles`** - Stores user profiles with personality traits
   - Columns: `user_id`, `email`, `phone_number`, `first_name`, `last_name`, `name`, `adventurous`, `cultural`, `foodie`, `nature_lover`, `history_buff`, `social`, `preferences` (JSON), `social_media_data` (JSON), `travel_history` (JSON), `created_at`, `updated_at`

2. **`interaction_logs`** - Stores user interaction history
   - Columns: `interaction_id`, `user_id`, `interaction_type`, `content` (JSON), `metadata` (JSON), `timestamp`

3. **`recommendation_scores`** - Stores recommendation match scores
   - Columns: `recommendation_id`, `user_id`, `item_id`, `item_name`, `category`, `match_score`, `personality_match_scores` (JSON), `recommendation_data` (JSON), `created_at`

4. **`chat_logs`** - Stores chat messages and responses
   - Columns: `chat_id`, `user_id`, `message`, `response`, `message_type`, `metadata` (JSON), `timestamp`

### Cost Considerations

- **BigQuery**: Free tier includes 10 GB storage and 1 TB queries per month
- **Cloud Storage**: Free tier includes 5 GB storage per month
- For production, monitor usage in [GCP Billing Console](https://console.cloud.google.com/billing)

### Installation

1. **Clone the repository:**
```bash
git clone <repo-url>
cd Bacolod_Tourist
```

2. **Install root dependencies:**
```bash
pnpm install
```

3. **Set up infrastructure services:**
```bash
# Start Redis (required for OTP/session). MongoDB in docker-compose is optional; primary DB is BigQuery.
docker-compose up -d
```

4. **Set up Google Cloud Platform:**
   - Follow the detailed [Google Cloud Platform Setup](#-google-cloud-platform-setup) guide above
   - Create BigQuery dataset and Cloud Storage bucket
   - Download service account credentials JSON file
   - Place credentials file in `backend/` directory

5. **Set up backend:**
```bash
cd backend
poetry install
# Create .env file with GCP configuration (see Environment Variables section below)
cd ..
```

6. **Set up frontend:**
```bash
cd frontend
# Create .env.local file (see Environment Variables section)
cd ..
```

7. **Run development servers:**
```bash
# From root directory - starts both frontend and backend
pnpm dev

# Or run separately:
# Terminal 1 - Backend:
cd backend && poetry shell && poetry run uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend:
cd frontend && pnpm dev
```

This will start:
- Frontend on http://localhost:3000
- Backend on http://localhost:8000

### Testing the MOGI Chatbot

1. Navigate to `http://localhost:3000/login`
2. Click the "Phone" tab
3. Enter:
   - Phone: `09123456789` (or any valid Philippine format: `+63 9XX XXX XXXX` or `09XX XXX XXXX`)
   - First Name: `Juan`
   - Last Name: `Dela Cruz`
4. Click "Send Verification Code"
5. Enter OTP: `000000` (dev mode dummy OTP)
6. Click "Verify & Login"
7. You'll be redirected to `/chat` where MOGI will automatically greet you with:
   - Personalized welcome message mentioning your personality
   - Comprehensive recommendations across all categories
   - Clickable links for each recommendation
   - Personality summary

## 📁 Project Structure

```
.
├── frontend/              # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/    # Phone/Email authentication
│   │   │   ├── chat/     # MOGI chatbot interface
│   │   │   ├── dashboard/# Main dashboard
│   │   │   ├── map/      # Interactive maps
│   │   │   ├── secret-recommendations/  # Secret spots page
│   │   │   └── safety/   # Safety information page (scams & danger zones)
│   │   ├── components/
│   │   │   ├── MOGIChatbot.tsx      # Main chatbot component
│   │   │   ├── PhoneInput.tsx        # Philippine phone input
│   │   │   ├── WelcomeMessage.tsx    # Welcome with recommendations
│   │   │   ├── RecommendationCard.tsx
│   │   │   └── RecommendationCategory.tsx
│   │   └── lib/
│   │       ├── api.ts    # FastAPI client
│   │       └── analytics.ts
│   └── ...
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── auth.py       # Authentication logic
│   │   ├── mogi_persona.py # MOGI persona definition
│   │   ├── make_client.py      # Make.com webhook client (optional)
│   │   ├── recommendation.py   # Recommendation engine (LangChain + FAISS)
│   │   ├── social_scraper.py # Bright Data + Scrapy social scraping
│   │   ├── personality_analyzer.py # LLM personality analysis
│   │   ├── personality_pipeline.py # Complete analysis pipeline
│   │   ├── welcome_message_service.py # Welcome message generation
│   │   ├── comprehensive_recommendations.py # All categories + InstantDB save + filtering
│   │   ├── instantdb_client.py # InstantDB user/recommendation persistence
│   │   ├── bigquery_retry_queue.py # Background BigQuery update retries
│   │   ├── sheets_sync.py # Google Sheet scraping & entity extraction
│   │   ├── content_scraper.py # Web scraping with Bright Data Web Unlocker
│   │   └── services/
│   │       └── entity_extractor.py # LLM-based multi-entity extraction
│   │   ├── scrapers/
│   │   │   ├── social_media_spider.py # Scrapy spiders (Facebook/Instagram)
│   │   │   ├── proxy_middleware.py # Bright Data proxy middleware
│   │   │   └── scrapy_settings.py # Scrapy configuration
│   │   ├── routes/
│   │   │   ├── auth_routes.py  # Phone/Email OTP auth
│   │   │   ├── chat_routes.py  # MOGI chat & welcome
│   │   │   ├── recommendation_routes.py
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── docker-compose.yml     # MongoDB & Redis
├── system_architecture.html # Architecture flowchart
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

# Test OpenAI connection
cd backend
poetry run python test_openai.py
```

## 🔐 Environment Variables

### Backend Required Variables (`backend/.env`)

```env
# Google Cloud Platform (Required - see Google Cloud Setup section above)
GCP_PROJECT_ID=gen-lang-client-0542256476
GCP_CREDENTIALS_PATH=backend/gen-lang-client-0542256476-399081ed3dc7.json
BIGQUERY_DATASET_ID=Inasal_app
GCS_BUCKET_NAME=inasal-app-storage
GCS_BUCKET_LOCATION=us

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET_KEY=your-secret-key-change-this-in-production
JWT_ALGORITHM=HS256

# Development Mode (enables dummy OTP "000000")
DEV_MODE=true

# Make.com Integration (optional - fallback to LangChain if not set)
MAKE_WEBHOOK_CHAT=https://hook.make.com/your-chat-webhook
MAKE_WEBHOOK_RECOMMENDATIONS=https://hook.make.com/your-recommendations-webhook
MAKE_WEBHOOK_PERSONA=https://hook.make.com/your-persona-webhook

# AI Services (required for MOGI chatbot)
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Bright Data (for social media scraping)
BRIGHT_DATA_API_TOKEN=your_bright_data_api_token
BRIGHT_DATA_ZONE=webscrape_amzn
BRIGHT_DATA_RESIDENTIAL_USERNAME=brd-customer-{CUSTOMER_ID}-zone-{ZONE_NAME}__proxy1
BRIGHT_DATA_RESIDENTIAL_PASSWORD=your_password
BRIGHT_DATA_RESIDENTIAL_ENDPOINT=brd.superproxy.io:33335

# InstantDB (optional - for real-time user/recommendation persistence)
INSTANTDB_APP_ID=your_instantdb_app_id
INSTANTDB_ADMIN_TOKEN=your_instantdb_admin_token

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Frontend Required Variables (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🚢 Deployment

The application is configured for deployment on:

- **Railway**: Backend (FastAPI)
- **Vercel**: Frontend (Next.js)
- **Google Cloud Platform**: 
  - BigQuery for database (user profiles, personality, recommendations, chat logs)
  - Cloud Storage for file storage
- **Redis Cloud**: Cache and session storage

## 📚 Documentation

- **[system_architecture.html](./system_architecture.html)** - Interactive architecture: data flow, BigQuery streaming buffer solution, timelines, and code locations
- **[Google Cloud Platform Setup](#-google-cloud-platform-setup)** - Detailed BigQuery and Cloud Storage setup instructions (see above)
- **backend/SCRAPY_SETUP.md** - Scrapy + Bright Data Residential Proxy setup guide (if present)

## 🆕 Recent Improvements

### Data Quality & Filtering Enhancements

**Hotels/Accommodations Filtering:**
- Excludes general articles/blog posts (e.g., "17 Tourist Spots in Bacolod...")
- Only shows specific hotel/accommodation entities
- Filters out test/placeholder entries
- Minimum 50% match score requirement

**Scams & Danger Zones Improvements:**
- **Merged Correlated Topics**: Similar scams/danger zones are combined into single entries
- **English Translation**: All content automatically translated to English using LLM
- **Location Filtering**: Only Bacolod-related items shown (excludes Manila, Sulu, Marawi, etc.)
- **Reference Cleaning**: Replaces "Tulfo" references with "local police"
- **Malformed Data Filtering**: Removes fragmented text and incorrect location entries
- **Dedicated Safety Page**: Separate `/safety` page with filtering (All/Scams/Danger Zones)

**Recommendation System:**
- All recommendations loaded from InstantDB scraped content (no static JSON)
- Duplicate detection and removal
- Personality keyword matching with improved scoring algorithm
- Source link hiding for better UX (shows Google search instead)

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

# 5. Deploy to production
git checkout main
git merge staging
git push origin main
```

## 🤝 Contributing

1. Create a feature branch from `staging`
2. Make your changes
3. Test thoroughly
4. Submit a pull request to `staging` branch

## 📄 License

MIT

---

---

## 📖 Complete Documentation

## 📖 System Architecture & Documentation

### 🎯 Key Documents

- **[system_architecture.html](system_architecture.html)** - **INTERACTIVE VISUAL GUIDE** (Open in browser)
  - Complete data flow diagrams
  - BigQuery streaming buffer problem and three-layer solution
  - Timeline visualization with status indicators
  - Before/After comparison
  - Code file locations and testing procedures
  - **Best for visual learners!**

### 🏗️ Understanding the BigQuery Streaming Buffer Issue

#### The Problem
When a user profile is created via streaming insert into BigQuery, the row enters a **streaming buffer for ~90 minutes**. During this time:
- ✅ Personality analysis works fine
- ❌ BigQuery refuses to UPDATE the row
- ❌ Frontend shows generic "We're still learning..." message
- ❌ Data never gets permanently saved

#### The Solution (3 Layers)

**Layer 1: In-Memory Cache** (`backend/app/user_profile.py`)
- Stores analyzed personality immediately
- Frontend fetches from cache (not BigQuery)
- Response time: microseconds (instant)
- Cleared after BigQuery successfully updates

**Layer 2: Background Retry System** (`backend/app/bigquery_retry_queue.py` - NEW)
- Runs every 2 minutes automatically
- Retry schedule: 2, 5, 10, 20, 30, 60 minutes
- Gives up after: 6 hours or 12 attempts
- No manual intervention needed

**Layer 3: Better SQL** (`backend/app/bigquery_client.py`)
- Uses MERGE statement (handles streaming buffer better)
- INSERT or UPDATE in single operation
- More reliable than DELETE+UPDATE

### 📊 Data Flow Overview

```
User Registers (T+0s)
    ├─→ Profile created in BigQuery (0.5 defaults)
    └─→ Personality analysis starts (background)

Analysis Completes (T+5s)
    ├─→ Traits calculated: {adventurous: 0.7, social: 0.9}
    ├─→ Store in CACHE immediately ✅
    ├─→ Try BigQuery update → FAILS (streaming buffer)
    └─→ Add to retry queue

Frontend Requests Profile (T+10s)
    ├─→ Get from cache ✅
    └─→ Display "I see you're adventurous!"

Background Retry (Every 2 minutes)
    ├─→ T+2min: Retry #1 → FAILS
    ├─→ T+5min: Retry #2 → FAILS
    └─→ ...continues retrying...

BigQuery Buffer Expires (T+90min)
    └─→ Background retry succeeds ✅
        BigQuery now has correct traits
        Cache cleared, retry queue cleaned up
```

### 🔧 Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `backend/app/main.py` | Modified | Start background retry task on app startup |
| `backend/app/personality_pipeline.py` | Modified | Use retry queue when BigQuery update fails |
| `backend/app/bigquery_client.py` | Updated | Use MERGE statement for better handling |
| `backend/app/user_profile.py` | Enhanced | In-memory cache for personality fallback |
| **`backend/app/bigquery_retry_queue.py`** | **NEW** | **Background automatic retry system** |

### ✅ Result

**Before:**
```
Backend: ✅ Personality Analysis Complete! (0.7, 0.9...)
BigQuery: ❌ Still has defaults (0.5, 0.5...)
Frontend: ❌ "We're still learning..." (wrong!)
```

**After:**
```
Backend: ✅ Personality Analysis Complete!
Cache: ✅ Stores analyzed traits immediately
Frontend: ✅ "I see you're adventurous (70%) and social (90%)!"
BigQuery: ⏳ Eventually updates (after ~90 minutes)
```

### 🧪 How to Test

1. Start backend: `poetry run uvicorn app.main:app --reload --port 8000`
2. Register a new user in frontend
3. Go to chat page **immediately**
4. **Should see:** Correct personality traits ✅
5. Check backend logs for either:
   - `✅ Successfully updated user profile` (immediate save)
   - `⚠️ Added to retry queue` (will save in background)

### 📚 For More Details

Open **[system_architecture.html](system_architecture.html)** in your browser for an interactive visual guide with timelines, diagrams, and code locations!

---

**Built with ❤️ for Bacolod, Philippines**
