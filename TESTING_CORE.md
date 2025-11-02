# Testing Core Functionality

Even if LangChain dependencies aren't fully installed, you can test core functionality!

## Quick Test (Works Now!)

### ✅ Core Tests Passed!

Great news - core tests are already passing! You can see:
- ✅ Config module
- ✅ Auth functions (OTP, JWT)  
- ✅ User profile models
- ✅ Database connection utilities
- ✅ Redis client

### Test 2: Start the Server

The server can now start without LangChain! Try:

```powershell
cd backend
& "$env:APPDATA\Python\Python313\Scripts\poetry.exe" run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will:
- ✅ Start successfully with core features
- ✅ Auth endpoints work
- ✅ Profile endpoints work
- ⚠️ AI endpoints (chat, recommendations) will return 503 (service unavailable) but won't crash

## Install Minimal Dependencies First

If full installation fails, install minimal dependencies:

```powershell
cd backend
# Backup original
copy pyproject.toml pyproject-full.toml

# Use minimal version temporarily
copy pyproject-minimal.toml pyproject.toml

# Install minimal dependencies
& "$env:APPDATA\Python\Python313\Scripts\poetry.exe" install

# Run core tests
& "$env:APPDATA\Python\Python313\Scripts\poetry.exe" run python scripts/test_core_functionality.py
```

## What Can Be Tested Without LangChain

✅ **Authentication**
- OTP generation and verification
- JWT token creation/validation
- User login flow

✅ **User Profiles**
- Profile creation
- Personality traits storage
- Preferences management

✅ **Database & Redis**
- MongoDB connection
- Redis caching
- Session management

✅ **Basic API Endpoints**
- Health checks
- Auth endpoints
- Profile endpoints

## What Requires LangChain (Can Skip For Now)

⏸️ **AI Features** (require LangChain)
- Recommendations (needs vector store)
- Chat agent (needs LLM)
- RAG engine (needs LLM)

## Testing Strategy

1. **First**: Test core functionality (auth, profiles, database)
2. **Then**: Install LangChain dependencies separately
3. **Finally**: Test full AI features

This way you can verify the foundation works while resolving dependency issues!

