# Quick Start Guide

## Step 1: Install Poetry Dependencies

Run this PowerShell script to automatically set up Poetry and install dependencies:

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File install-poetry.ps1
cd ..
```

**Or manually:**
```powershell
cd backend
& "$env:APPDATA\Python\Python313\Scripts\poetry.exe" install
cd ..
```

**Note:** The `&` operator is required in PowerShell to execute a command from a string path!

## Step 2: Verify Setup

```powershell
# Check Docker is running
docker ps

# Check Poetry works (if PATH is set)
poetry --version

# Or use direct path
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" --version
```

## Step 3: Start Services

```powershell
# Start MongoDB and Redis
docker-compose up -d

# Start backend (in one terminal)
pnpm --filter backend dev

# Run tests (in another terminal)
pnpm --filter backend test
```

## Alternative: Direct Poetry Commands

If Poetry isn't on PATH, you can use the full path directly:

```powershell
# Install dependencies
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" install

# Run tests
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" run pytest

# Start server
& "$env:APPDATA\Roaming\Python\Python313\Scripts\poetry.exe" run uvicorn app.main:app --reload
```

## Make Poetry Permanent (Optional)

To add Poetry to PATH permanently:

1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "User variables", select "Path" and click "Edit"
5. Click "New" and add: `C:\Users\jonel\AppData\Roaming\Python\Python313\Scripts`
6. Click OK on all dialogs
7. Restart your terminal

