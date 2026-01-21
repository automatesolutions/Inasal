# 🚀 How to Start the Web App (Backend & Frontend)

This guide will walk you through starting both the backend and frontend of the Bacolod Tourist MOGI Chatbot application.

## 📋 Prerequisites

Before starting, make sure you have:
- ✅ Node.js >= 18 installed
- ✅ pnpm >= 9 installed
- ✅ Python >= 3.11 installed
- ✅ Poetry installed (for Python dependency management)
- ✅ Docker and Docker Compose installed (for MongoDB and Redis)

## 🔧 Step-by-Step Startup Guide

### Step 1: Start Infrastructure Services (MongoDB & Redis)

First, start the required database services using Docker Compose:

```bash
# From the project root directory
docker-compose up -d
```

This will start:
- **MongoDB** on port `27017`
- **Redis** on port `6379`

Verify they're running:
```bash
docker ps
```

You should see `bacolod-mongodb` and `bacolod-redis` containers running.

### Step 2: Configure Environment Variables

#### Backend Environment Variables

Create or update `backend/.env` file:

```env
# Database
DATABASE_URL=mongodb://localhost:27017/bacolod_tourist
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

# Bright Data (optional - for social media scraping)
BRIGHT_DATA_API_TOKEN=your_bright_data_api_token
BRIGHT_DATA_ZONE=webscrape_amzn
BRIGHT_DATA_RESIDENTIAL_USERNAME=brd-customer-{CUSTOMER_ID}-zone-{ZONE_NAME}__proxy1
BRIGHT_DATA_RESIDENTIAL_PASSWORD=your_password
BRIGHT_DATA_RESIDENTIAL_ENDPOINT=brd.superproxy.io:33335

# CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

#### Frontend Environment Variables

Create or update `frontend/.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Step 3: Install Dependencies

#### Install Root Dependencies

```bash
# From project root
pnpm install
```

#### Install Backend Dependencies

```bash
cd backend
poetry install
cd ..
```

#### Install Frontend Dependencies

```bash
cd frontend
pnpm install
cd ..
```

### Step 4: Start the Application

You have **two options** to start the app:

#### Option A: Start Both Together (Recommended)

From the project root directory:

```bash
pnpm dev
```

This will start both frontend and backend simultaneously.

#### Option B: Start Separately (For Debugging)

**Terminal 1 - Backend:**
```bash
cd backend
poetry shell
poetry run uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
pnpm dev
```

### Step 5: Verify Everything is Running

After starting, you should see:

- ✅ **Backend API**: http://localhost:8000
  - Health check: http://localhost:8000/health
  - API docs: http://localhost:8000/docs

- ✅ **Frontend App**: http://localhost:3000
  - Login page: http://localhost:3000/login
  - Chat page: http://localhost:3000/chat (after login)

## 🧪 Testing the Application

### Test Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "bacolod-tourist-api"}
```

### Test Frontend

1. Open your browser and navigate to: http://localhost:3000/login
2. Click the "Phone" tab
3. Enter:
   - Phone: `09123456789` (or any valid Philippine format)
   - First Name: `Juan`
   - Last Name: `Dela Cruz`
4. Click "Send Verification Code"
5. Enter OTP: `000000` (dev mode dummy OTP)
6. Click "Verify & Login"
7. You'll be redirected to `/chat` where MOGI will greet you!

### Test OpenAI Connection

```bash
cd backend
poetry run python test_openai.py
```

## 🛑 Stopping the Application

### Stop Frontend & Backend

Press `Ctrl+C` in the terminal where you started the services.

### Stop Infrastructure Services

```bash
docker-compose down
```

To also remove volumes (clears data):
```bash
docker-compose down -v
```

## 🔍 Troubleshooting

### Backend won't start

1. **Check if MongoDB is running:**
   ```bash
   docker ps | grep mongodb
   ```

2. **Check if Redis is running:**
   ```bash
   docker ps | grep redis
   ```

3. **Check backend logs:**
   ```bash
   cd backend
   poetry run uvicorn app.main:app --reload --port 8000
   ```
   Look for error messages in the terminal.

4. **Verify environment variables:**
   Make sure `backend/.env` exists and has all required variables, especially `OPENAI_API_KEY`.

### Frontend won't start

1. **Check if backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check frontend logs:**
   Look for error messages in the terminal where you ran `pnpm dev`.

3. **Verify environment variables:**
   Make sure `frontend/.env.local` exists with `NEXT_PUBLIC_API_URL=http://localhost:8000`.

### Port already in use

If you get a "port already in use" error:

**For backend (port 8000):**
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # Mac/Linux
```

**For frontend (port 3000):**
```bash
# Find process using port 3000
netstat -ano | findstr :3000  # Windows
lsof -i :3000                 # Mac/Linux

# Kill the process
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # Mac/Linux
```

### MongoDB connection error

1. **Check if MongoDB container is running:**
   ```bash
   docker ps | grep mongodb
   ```

2. **Check MongoDB logs:**
   ```bash
   docker logs bacolod-mongodb
   ```

3. **Restart MongoDB:**
   ```bash
   docker-compose restart mongodb
   ```

### Redis connection error

1. **Check if Redis container is running:**
   ```bash
   docker ps | grep redis
   ```

2. **Check Redis logs:**
   ```bash
   docker logs bacolod-redis
   ```

3. **Restart Redis:**
   ```bash
   docker-compose restart redis
   ```

## 📝 Quick Reference

### Common Commands

```bash
# Start everything
docker-compose up -d    # Start MongoDB & Redis
pnpm dev                # Start frontend & backend

# Stop everything
Ctrl+C                  # Stop frontend & backend
docker-compose down     # Stop MongoDB & Redis

# Check status
docker ps               # Check containers
curl http://localhost:8000/health  # Check backend
```

### Development URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Backend Health: http://localhost:8000/health

---

**Need help?** Check the main [README.md](./README.md) for more detailed information.
