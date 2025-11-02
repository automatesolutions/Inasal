# Troubleshooting Guide

Common issues and solutions for the Bacolod Tourist project.

## Docker Issues

### Docker Desktop Not Running

**Error:**
```
unable to get image 'redis:7-alpine': error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/redis:7-alpine/json": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

**Solution:**
1. **Start Docker Desktop**
   - Open Docker Desktop application on Windows
   - Wait until Docker Desktop shows "Docker Desktop is running" (whale icon in system tray)

2. **Verify Docker is running:**
   ```powershell
   docker ps
   ```
   Should show running containers (or empty list, but no error)

3. **Then try docker-compose again:**
   ```powershell
   docker-compose up -d
   ```

### Docker Compose Version Warning

**Warning:**
```
the attribute `version` is obsolete, it will be ignored
```

**Solution:** This is harmless. The `version` field has been removed from docker-compose.yml. You can ignore this warning.

## Poetry Issues

### "poetry is not recognized"

**Solution:**
1. Install Poetry:
   ```powershell
   pip install poetry
   ```

2. If still not recognized after installation:
   - Restart your terminal/PowerShell
   - Or add Poetry to PATH manually (see INSTALL_POETRY.md)

3. Verify:
   ```powershell
   poetry --version
   ```

## MongoDB/Redis Connection Errors

### Backend can't connect to MongoDB or Redis

**Error:**
```
Failed to connect to MongoDB: ...
Failed to connect to Redis: ...
```

**Solutions:**

1. **Check Docker containers are running:**
   ```powershell
   docker-compose ps
   ```
   Should show `mongodb` and `redis` containers as "Up"

2. **Start containers if not running:**
   ```powershell
   docker-compose up -d
   ```

3. **Check logs if containers are failing:**
   ```powershell
   docker-compose logs mongodb
   docker-compose logs redis
   ```

4. **Restart containers:**
   ```powershell
   docker-compose restart
   ```

## Python/Backend Issues

### "pytest is not recognized"

**Solution:**
```powershell
cd backend
poetry install
```

### "Module not found" errors

**Solution:**
1. Make sure dependencies are installed:
   ```powershell
   cd backend
   poetry install
   ```

2. Make sure you're using `poetry run`:
   ```powershell
   poetry run pytest
   poetry run python scripts/test_api_endpoints.py
   ```

### Import errors (LangChain, FastAPI, etc.)

**Solution:**
- Dependencies might not be installed
- Run: `cd backend && poetry install`

## Frontend Issues

### "node_modules missing"

**Solution:**
```powershell
pnpm install
```

### Port already in use (3000 or 8000)

**Solution:**
1. Find what's using the port:
   ```powershell
   # Windows
   netstat -ano | findstr :3000
   netstat -ano | findstr :8000
   ```

2. Kill the process or change the port in configuration

## API Testing Issues

### API tests fail with connection errors

**Error:**
```
Connection refused
ConnectionError
```

**Solution:**
1. Make sure backend server is running:
   ```powershell
   pnpm --filter backend dev
   ```

2. Wait for server to fully start (look for "Application startup complete")

3. Then run API tests in another terminal

### OTP verification fails

**Solution:**
- In development, OTP is printed to console
- Check backend terminal output for OTP code
- Use that code for verification

## Vector Store Issues

### "Vector store not initialized"

**Solution:**
Run the ingestion script:
```powershell
pnpm --filter backend ingest
```

This creates the FAISS vector store from attractions.json

## General Checklist

Before reporting issues, check:

- [ ] Docker Desktop is running
- [ ] MongoDB and Redis containers are up (`docker-compose ps`)
- [ ] Poetry is installed (`poetry --version`)
- [ ] Backend dependencies installed (`cd backend && poetry install`)
- [ ] Frontend dependencies installed (`pnpm install`)
- [ ] Backend server is running (`pnpm --filter backend dev`)
- [ ] Environment variables are set (`.env` file in backend/)

## Getting Help

If issues persist:
1. Check all logs: `docker-compose logs`
2. Check backend logs in terminal where server is running
3. Verify all prerequisites from SETUP.md are installed
4. Try restarting Docker Desktop and rebuilding containers:
   ```powershell
   docker-compose down
   docker-compose up -d
   ```

