# Quick Setup Instructions

## Overview

The migration to hybrid architecture (FastAPI + Strapi + Make.com) has been implemented. Follow these steps to complete the setup.

## Prerequisites

- Node.js >= 18
- Python >= 3.11
- Poetry
- PostgreSQL (for Strapi production) or SQLite (for development)
- Make.com account (free tier available)

## Step 1: Set Up Strapi

1. **Install Strapi:**
   ```bash
   npx create-strapi-app@latest strapi-backend --quickstart
   cd strapi-backend
   npm run develop
   ```

2. **Create Content Types:**
   - Follow the detailed guide in `STRAPI_SETUP_GUIDE.md`
   - Create: User Profile, Attraction, Interaction Log, Recommendation
   - Configure permissions

3. **Create API Token:**
   - Go to Settings → API Tokens
   - Create token with "Full access"
   - Copy the token

## Step 2: Set Up Make.com

1. **Create Account:**
   - Sign up at https://www.make.com
   - Create a new organization/workspace

2. **Create Workflows:**
   - Follow the detailed guide in `MIGRATION_GUIDE.md` (Phase 2)
   - Create: Chat workflow, Recommendations workflow, Persona discovery workflow
   - Copy webhook URLs

## Step 3: Configure Backend

1. **Update `.env` file:**
   ```env
   # Strapi Configuration
   STRAPI_URL=http://localhost:1337
   STRAPI_API_TOKEN=your_strapi_token_here

   # Make.com Webhooks
   MAKE_WEBHOOK_CHAT=https://hook.make.com/your-chat-webhook
   MAKE_WEBHOOK_RECOMMENDATIONS=https://hook.make.com/your-recommendations-webhook
   MAKE_WEBHOOK_PERSONA=https://hook.make.com/your-persona-webhook
   ```

2. **Install Dependencies:**
   ```bash
   cd backend
   poetry install
   ```

3. **Start Backend:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

## Step 4: Migrate Data

Run the migration script to move data from MongoDB to Strapi:

```bash
cd backend
poetry run python scripts/migrate_to_strapi.py
```

This will migrate:
- User profiles
- Attractions
- Interaction logs (optional)

## Step 5: Start Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

## Step 6: Test

1. **Test Authentication:**
   - Go to http://localhost:3000/login
   - Send OTP and verify

2. **Test Chat:**
   - Go to http://localhost:3000/chat
   - Send a message (should go through Make.com)

3. **Test Recommendations:**
   - Go to http://localhost:3000/dashboard
   - Recommendations should load from Strapi

## Architecture Flow

```
User → Frontend (Next.js)
  ↓
FastAPI (Orchestration)
  ↓
├─→ Strapi (Content: Profiles, Attractions)
└─→ Make.com (AI: Chat, Recommendations, Persona)
```

## Fallback Behavior

The system gracefully falls back to legacy implementations:
- If Strapi is not configured → Uses MongoDB
- If Make.com is not configured → Uses LangChain
- Both can work simultaneously during migration

## Troubleshooting

### Strapi Connection Issues

- Verify `STRAPI_URL` is correct
- Check API token permissions
- Ensure Strapi is running on port 1337

### Make.com Webhook Issues

- Verify webhook URLs are correct
- Check Make.com scenario is active
- Review Make.com execution logs

### Migration Issues

- Ensure Strapi content types are created
- Check API token has full access
- Verify MongoDB connection

## Next Steps

1. ✅ Complete Strapi setup (see STRAPI_SETUP_GUIDE.md)
2. ✅ Set up Make.com workflows (see MIGRATION_GUIDE.md Phase 2)
3. ✅ Configure environment variables
4. ✅ Run migration script
5. ✅ Test all features
6. ✅ Deploy to production

## Documentation

- **Detailed Migration Guide:** `MIGRATION_GUIDE.md`
- **Strapi Setup:** `STRAPI_SETUP_GUIDE.md`
- **Architecture Summary:** `ARCHITECTURE_MIGRATION_SUMMARY.md`
- **Project Plan:** `plan.md` (Phase 9)

