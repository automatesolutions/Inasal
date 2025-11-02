# Setup Guide

Follow these steps to get the Bacolod Tourist app running locally.

## Prerequisites

1. **Node.js** (>= 18) and **pnpm** (>= 9)
   ```bash
   # Install pnpm if not already installed
   npm install -g pnpm
   ```

2. **Python** (>= 3.11) and **Poetry**
   
   **Windows (PowerShell):**
   ```powershell
   # Install Poetry using the official installer
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   
   # Add Poetry to PATH (restart terminal after this)
   $env:Path += ";$env:APPDATA\Python\Scripts"
   ```
   
   **Or using pip (simpler but not recommended):**
   ```bash
   pip install poetry
   ```
   
   **Linux/Mac:**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   # Then add to PATH (usually ~/.local/bin)
   ```
   
   **Verify installation:**
   ```bash
   poetry --version
   ```

3. **Docker** and **Docker Compose** (for MongoDB and Redis)

## Setup Steps

### 1. Install Root Dependencies

```bash
pnpm install
```

### 2. Setup Backend

```bash
cd backend
poetry install
cp .env.example .env
# Edit .env with your configuration (especially OPENAI_API_KEY)
cd ..
```

### 3. Start Infrastructure Services

```bash
docker-compose up -d
```

This starts:
- MongoDB on `localhost:27017`
- Redis on `localhost:6379`

### 4. Run Development Servers

From the root directory:

```bash
# Run both frontend and backend
pnpm dev

# Or run separately:
pnpm dev:frontend  # Frontend on http://localhost:3000
pnpm dev:backend   # Backend on http://localhost:8000
```

### 5. Verify Setup

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing

```bash
# Frontend tests
pnpm --filter frontend test

# Backend tests
pnpm --filter backend test

# All tests
pnpm test
```

## Troubleshooting

### Backend Import Errors

If you see import errors for LangChain packages, ensure Poetry dependencies are installed:

```bash
cd backend
poetry install
```

### MongoDB/Redis Connection Issues

Ensure Docker containers are running:

```bash
docker-compose ps
docker-compose up -d
```

### Port Already in Use

- Frontend default port: 3000
- Backend default port: 8000

Change these in the respective configuration files if needed.

