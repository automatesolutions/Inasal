# Testing Core Functionality

Even if LangChain dependencies aren't fully installed, you can test core functionality!

## Quick Test (No Dependencies Needed)

### Test 1: Core Module Imports

This tests that basic Python modules work:

```powershell
cd backend
& "$env:APPDATA\Python\Python313\Scripts\poetry.exe" run python scripts/test_core_functionality.py
```

Or if Poetry environment is set up:

```powershell
pnpm --filter backend run test-core
```

This will test:
- ✅ Config module
- ✅ Auth functions (OTP, JWT)
- ✅ User profile models
- ✅ Database connection utilities
- ✅ Redis client

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

