# Strapi Setup Guide

This guide will help you set up Strapi CMS for the Bacolod Tourist application.

## Prerequisites

- Node.js >= 18
- npm or yarn
- PostgreSQL (recommended) or SQLite (for development)

## Step 1: Install Strapi

```bash
# Create Strapi project
npx create-strapi-app@latest strapi-backend --quickstart

# Or with PostgreSQL (recommended for production)
npx create-strapi-app@latest strapi-backend \
  --quickstart \
  --dbclient=postgres \
  --dbname=bacolod_tourist \
  --dbhost=localhost \
  --dbport=5432 \
  --dbusername=postgres \
  --dbpassword=yourpassword

cd strapi-backend
```

## Step 2: Start Strapi

```bash
npm run develop
```

Access the admin panel at: `http://localhost:1337/admin`

Create your admin account when prompted.

## Step 3: Create Content Types

### A. User Profile

1. Go to **Content-Type Builder** → **Create new collection type**
2. Display name: `User Profile`
3. API ID: `user-profile`
4. Enable **Draft & Publish**

**Add Fields:**

| Field Name | Type | Required | Unique | Default |
|------------|------|----------|--------|---------|
| `user_id` | Text | Yes | Yes | - |
| `email` | Email | Yes | Yes | - |
| `name` | Text | No | No | - |
| `personality` | JSON | No | No | `{}` |
| `preferences` | JSON | No | No | `{}` |
| `travel_history` | JSON | No | No | `[]` |

**Permissions:**
- Public: None
- Authenticated: Find, FindOne, Create, Update, Delete (own profile only)

### B. Attraction

1. Go to **Content-Type Builder** → **Create new collection type**
2. Display name: `Attraction`
3. API ID: `attraction`
4. Enable **Draft & Publish**

**Add Fields:**

| Field Name | Type | Required | Unique | Default |
|------------|------|----------|--------|---------|
| `name` | Text | Yes | No | - |
| `type` | Enumeration | Yes | No | Options: `historical`, `cultural`, `food`, `nature`, `entertainment` |
| `description` | Rich Text | Yes | No | - |
| `tags` | JSON | No | No | `[]` |
| `best_time_to_visit` | Text | No | No | - |
| `entry_fee` | Text | No | No | - |
| `personality_match` | JSON | No | No | `{}` |
| `images` | Media (Multiple) | No | No | - |

**Create Component: Location**

1. Go to **Components** → **Create new component**
2. Display name: `Location`
3. Category: `shared`
4. Add fields:
   - `address` (Text, Required)
   - `latitude` (Number, Required)
   - `longitude` (Number, Required)

5. Add `location` field to Attraction:
   - Type: Component
   - Component: `shared.location`
   - Required: Yes

**Permissions:**
- Public: Find, FindOne
- Authenticated: Find, FindOne

### C. Interaction Log

1. Go to **Content-Type Builder** → **Create new collection type**
2. Display name: `Interaction Log`
3. API ID: `interaction-log`
4. Disable **Draft & Publish**

**Add Fields:**

| Field Name | Type | Required | Unique | Default |
|------------|------|----------|--------|---------|
| `user` | Relation (Many-to-One) | Yes | No | Related to: User Profile |
| `interaction_type` | Enumeration | Yes | No | Options: `chat`, `search`, `view_destination`, `like`, `bookmark` |
| `content` | JSON | No | No | `{}` |
| `metadata` | JSON | No | No | `{}` |
| `timestamp` | DateTime | Auto | No | Now |

**Permissions:**
- Public: None
- Authenticated: Create (own logs), Find (own logs), FindOne (own logs)

### D. Recommendation

1. Go to **Content-Type Builder** → **Create new collection type**
2. Display name: `Recommendation`
3. API ID: `recommendation`
4. Disable **Draft & Publish**

**Add Fields:**

| Field Name | Type | Required | Unique | Default |
|------------|------|----------|--------|---------|
| `user` | Relation (Many-to-One) | Yes | No | Related to: User Profile |
| `hotels` | JSON | No | No | `[]` |
| `restaurants` | JSON | No | No | `[]` |
| `entertainment` | JSON | No | No | `[]` |
| `tourist_spots` | JSON | No | No | `[]` |
| `secret_recommendations` | JSON | No | No | `[]` |
| `created_at` | DateTime | Auto | No | Now |
| `expires_at` | DateTime | No | No | - |

**Permissions:**
- Public: None
- Authenticated: Find (own recommendations), FindOne (own recommendations), Create (via API)

## Step 4: Configure API Tokens

1. Go to **Settings** → **API Tokens**
2. Click **Create new API Token**
3. Configure:
   - Name: `Make.com Integration`
   - Token duration: Unlimited
   - Token type: **Full access**
4. Copy the token (you'll need it for backend `.env`)

## Step 5: Configure Authentication

1. Go to **Settings** → **Users & Permissions Plugin** → **Advanced Settings**
2. Configure:
   - JWT expiration: `7d` (or your preferred duration)
   - Email confirmation: Disabled (using OTP instead)
   - Email reset password: Configure if needed

## Step 6: Set Up Email Provider (Optional)

If you want Strapi to send emails:

1. Go to **Settings** → **Email plugin**
2. Configure your SMTP settings:
   - Provider: Custom SMTP
   - SMTP Host: Your SMTP host
   - SMTP Port: 587
   - Username: Your SMTP username
   - Password: Your SMTP password

## Step 7: Update Backend Configuration

Add to your `backend/.env`:

```env
# Strapi Configuration
STRAPI_URL=http://localhost:1337
STRAPI_API_TOKEN=your_api_token_here
```

## Step 8: Test Strapi API

Test the API endpoints:

```bash
# Get attractions (public)
curl http://localhost:1337/api/attractions

# Get user profile (requires auth)
curl http://localhost:1337/api/user-profiles \
  -H "Authorization: Bearer YOUR_API_TOKEN"
```

## Step 9: Run Migration Script

After setting up Strapi, run the migration script:

```bash
cd backend
poetry run python scripts/migrate_to_strapi.py
```

This will migrate:
- User profiles from MongoDB
- Attractions from JSON file
- Interaction logs (optional)

## Troubleshooting

### Issue: API returns 403 Forbidden

**Solution:** Check content type permissions in Strapi admin panel:
1. Go to **Settings** → **Users & Permissions Plugin** → **Roles**
2. Select the role (Public or Authenticated)
3. Enable the required permissions for each content type

### Issue: Cannot create user profile via API

**Solution:** Ensure the API token has full access:
1. Go to **Settings** → **API Tokens**
2. Verify token type is "Full access"

### Issue: Relations not working

**Solution:** Ensure relations are set up correctly:
1. Check that the relation field exists in both content types
2. Verify the relation type (Many-to-One, One-to-Many, etc.)
3. Ensure permissions allow creating relations

## Next Steps

After Strapi is set up:

1. ✅ Configure Make.com workflows (see MIGRATION_GUIDE.md)
2. ✅ Update backend `.env` with Strapi credentials
3. ✅ Run migration script
4. ✅ Test API endpoints
5. ✅ Update frontend if needed (should work as-is since FastAPI proxies)

## Production Deployment

For production:

1. Use PostgreSQL instead of SQLite
2. Set up proper environment variables
3. Configure CORS settings
4. Set up SSL/TLS
5. Configure backup strategy
6. Set up monitoring and logging

See Strapi documentation for production deployment: https://docs.strapi.io/dev-docs/deployment

