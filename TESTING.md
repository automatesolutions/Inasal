# Testing Guide

This guide helps you test the Bacolod Tourist API to ensure everything is working correctly before proceeding to Phase 5.

## Prerequisites

1. **Start Infrastructure Services**
   ```bash
   docker-compose up -d
   ```
   This starts MongoDB and Redis.

2. **Start Backend Server**
   ```bash
   cd backend
   poetry install  # If not already installed
   poetry run uvicorn app.main:app --reload
   ```
   Or from root:
   ```bash
   pnpm --filter backend dev
   ```

3. **Set Environment Variables**
   Make sure `backend/.env` has at least:
   ```env
   OPENAI_API_KEY=your_key_here  # Optional but recommended for full testing
   DATABASE_URL=mongodb://localhost:27017/bacolod_tourist
   REDIS_URL=redis://localhost:6379
   ```

## Running Tests

### 1. Unit Tests

Run backend unit tests:
```bash
cd backend
poetry run pytest
```

Or from root:
```bash
pnpm --filter backend test
```

This tests:
- Authentication functions
- User profile operations
- Recommendation engine logic
- RAG engine functionality

### 2. API Endpoint Tests

We've created a script to test all API endpoints:

```bash
cd backend
poetry run python scripts/test_api_endpoints.py
```

Or from root:
```bash
pnpm --filter backend run test-api
```

**Note:** Add this script to `backend/package.json`:
```json
"test-api": "python scripts/test_api_endpoints.py"
```

### 3. Manual API Testing

You can also test endpoints manually using:

**Option A: Using curl**
```bash
# Health check
curl http://localhost:8000/health

# Get weather (no auth required)
curl http://localhost:8000/api/rag/weather

# Send OTP
curl -X POST http://localhost:8000/api/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'

# Verify OTP (use the OTP from console/email)
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "otp": "123456"}'

# Get profile (requires auth token from verify-otp)
curl http://localhost:8000/api/profile/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get recommendations (requires auth)
curl http://localhost:8000/api/recommendations/?limit=5 \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

**Option B: Using the API Docs**
Open in browser: http://localhost:8000/docs

This provides an interactive Swagger UI where you can test all endpoints.

## Test Checklist

Before proceeding to Phase 5, verify:

### ✅ Infrastructure
- [ ] MongoDB is running and accessible
- [ ] Redis is running and accessible
- [ ] Backend server starts without errors

### ✅ Authentication
- [ ] Health check endpoint works
- [ ] Send OTP endpoint works
- [ ] OTP verification works (check console for OTP code)
- [ ] JWT token is returned correctly

### ✅ User Profile
- [ ] Get profile endpoint works
- [ ] Update personality endpoint works
- [ ] Update preferences endpoint works

### ✅ Recommendations
- [ ] Get recommendations endpoint works
- [ ] Recommendations include weather context
- [ ] Hidden gems endpoint works
- [ ] Recommendations are personalized

### ✅ RAG Engine
- [ ] Weather endpoint returns data
- [ ] Events endpoint returns data
- [ ] News endpoint returns data
- [ ] Local tips endpoint works (requires OpenAI API key)

### ✅ Data
- [ ] Attractions data is loaded (check logs)
- [ ] Vector store is initialized (check logs)
- [ ] Recommendations use vector search

## Common Issues

### MongoDB Connection Error
```
Error: Failed to connect to MongoDB
```
**Solution:** Make sure MongoDB is running: `docker-compose up -d`

### Redis Connection Error
```
Error: Failed to connect to Redis
```
**Solution:** Make sure Redis is running: `docker-compose up -d`

### No Recommendations Returned
```
Warning: Vector store not initialized
```
**Solution:** Run the ingestion script:
```bash
pnpm --filter backend ingest
```

### OpenAI API Errors
```
Error: API key not configured
```
**Solution:** Add `OPENAI_API_KEY` to `backend/.env`. Without it, some features will use mock data.

## Next Steps

Once all tests pass:
1. ✅ Verify all checklist items
2. ✅ Review any error logs
3. ✅ Test a complete user flow (login → recommendations → chat)
4. 🚀 Proceed to Phase 5: LangGraph Flows & Itinerary Builder

