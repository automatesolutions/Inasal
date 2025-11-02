# Frontend Testing & Verification Guide

## Quick Start - Verify Frontend is Working

### 1. Start the Development Server

```powershell
cd frontend
pnpm dev
```

The server will start at `http://localhost:3000`

### 2. Check the Frontend Manually

Open your browser and visit:
- **Home Page**: http://localhost:3000
- **Login Page**: http://localhost:3000/login
- **Dashboard**: http://localhost:3000/dashboard
- **Chat**: http://localhost:3000/chat
- **Map**: http://localhost:3000/map

### 3. Run Component Tests

Test individual React components:

```powershell
cd frontend
pnpm test
```

Or run with coverage:
```powershell
pnpm test:coverage
```

### 4. Run E2E Tests (End-to-End)

Make sure the dev server is running first, then:

```powershell
cd frontend
pnpm test:e2e
```

Or with UI mode (visual):
```powershell
pnpm test:e2e:ui
```

## Test Results Summary

### ✅ Component Tests (19 tests passing)
- **LoginPage** (5 tests)
  - Renders login form
  - Email input works
  - OTP form appears after submission
  - Change email functionality
  - Form validation

- **DashboardPage** (5 tests)
  - Renders dashboard title
  - Recommended destinations section
  - Hidden gems section
  - Cultural highlights section
  - Layout structure

- **ChatPage** (6 tests)
  - Renders chat interface
  - Empty state message
  - User can type messages
  - Message submission
  - Loading states
  - Empty message validation

- **HomePage** (3 tests)
  - Welcome message
  - Get started button
  - Styling classes

### ⏸️ E2E Tests
- Login journey test (requires dev server running)

## What to Verify Manually

### ✅ Login Page (`/login`)
1. Should show "Welcome Back!" heading
2. Email input field should be visible
3. "Send Verification Code" button should work
4. After submitting email, OTP form should appear
5. "Change Email" button should return to email form

### ✅ Dashboard (`/dashboard`)
1. Should show "Your Personalized Bacolod Experience" title
2. Three cards: Recommended, Hidden Gems, Cultural Highlights
3. Proper Bacolod-themed styling (amber/orange colors)

### ✅ Chat (`/chat`)
1. Should show "Chat with Your Local Guide" heading
2. Empty state message visible
3. Input field and Send button visible
4. Can type and send messages (placeholder response for now)
5. Loading animation appears when sending

### ✅ Home Page (`/`)
1. "Welcome to Bacolod" heading
2. "Get Started" button links to `/login`

## Troubleshooting

### Port 3000 already in use?
Change the port:
```powershell
pnpm dev -- -p 3001
```

### Tests failing?
1. Make sure all dependencies are installed:
   ```powershell
   pnpm install
   ```

2. Check if Next.js is properly configured

3. Clear `.next` cache:
   ```powershell
   rm -r .next  # Linux/Mac
   Remove-Item -Recurse -Force .next  # PowerShell
   ```

### E2E tests need Playwright browsers?
Install browsers:
```powershell
pnpm exec playwright install chromium
```

## Integration with Backend

To test with the backend API:

1. **Start Backend** (in separate terminal):
   ```powershell
   cd backend
   & "$env:APPDATA\Python\Python313\Scripts\poetry.exe" run uvicorn app.main:app --reload --port 8000
   ```

2. **Update API endpoint** in frontend components (when ready):
   - Currently using placeholder/mock data
   - Will need to connect to `http://localhost:8000/api/...`

## Next Steps

- [ ] Connect LoginPage to backend `/api/auth/send-otp` endpoint
- [ ] Connect ChatPage to backend `/api/chat` endpoint
- [ ] Connect Dashboard to backend `/api/recommendations` endpoint
- [ ] Add more E2E tests for full user journeys
- [ ] Add visual regression tests (optional)

