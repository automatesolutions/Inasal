# Quick Testing Guide

## Prerequisites Setup

1. **Install pnpm dependencies** (if not done):
   ```bash
   pnpm install
   ```

2. **Install Python dependencies via Poetry**:
   ```bash
   cd backend
   poetry install
   cd ..
   ```

3. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```

## Running Tests

### Unit Tests (Backend)
```bash
# From root directory
pnpm --filter backend test

# OR from backend directory
cd backend
poetry run pytest
```

### API Endpoint Tests
```bash
# Make sure backend server is running first!
pnpm --filter backend dev

# In another terminal, run API tests:
pnpm --filter backend run test-api
```

### Manual Testing via API Docs
1. Start backend: `pnpm --filter backend dev`
2. Open browser: http://localhost:8000/docs
3. Test endpoints interactively

## Common Issues

### "pytest is not recognized"
**Solution:** Make sure Poetry dependencies are installed:
```bash
cd backend
poetry install
```

### "node_modules missing"
**Solution:** Install pnpm dependencies:
```bash
pnpm install
```

### MongoDB/Redis Connection Errors
**Solution:** Start Docker containers:
```bash
docker-compose up -d
```

### "Module not found" errors
**Solution:** Make sure you're in the correct directory and Poetry env is activated:
```bash
cd backend
poetry shell
poetry install
```

