# Google Sheet Scraping & Recommendation Workflow

## Overview

This system scrapes ALL URLs from the Google Sheet, organizes data into separate category workspaces, updates only when new links are added, and uses this data for personality-aligned recommendations.

## 📋 Categories (Workspaces)

The system organizes scraped data into these category workspaces:

1. **Accommodation & Hotels** (`accommodation_hotels`)
2. **Tourist Spots & Hidden Gems** (`tourist_spots`)
3. **Restaurants & Food** (`restaurants_food`)
4. **Dangerous Areas & Travel Warnings** (`dangerous_areas`)
5. **Scams to Watch Out For** (`scams`)
6. **Secret Places in Bacolod** (`secret_places`)

## 🔄 Workflow

### Step 1: Sync Google Sheet
- Fetches all URLs from the Google Sheet
- Parses categories based on section headers
- Maps to internal category slugs

### Step 2: Detect New Links
- Compares current URLs with stored URLs using `content_hash`
- Only updates categories when new links are detected
- Tracks which categories have changes

### Step 3: Scrape All URLs
- Scrapes ALL URLs from ALL categories
- Uses smart router to select appropriate scraper:
  - Scrapy spiders for complex sites (TripAdvisor, Facebook, news sites)
  - ContentScraper for simple sites
- Extracts structured data:
  - Title, description, content text
  - Images
  - Location (address, coordinates)
  - Events (dates, names)
  - Personality keywords

### Step 4: Save to InstantDB
- Saves scraped content organized by category
- Each category is a separate "workspace" in InstantDB
- Updates only when new links detected (unless forced)

### Step 5: Use for Recommendations
- Recommendation system loads scraped content by category
- Matches items using:
  - Name similarity
  - Location proximity
  - Personality keyword alignment
  - Event dates (if user has travel dates)
- Enhances recommendations with scraped data:
  - Rich descriptions
  - Images from websites
  - Accurate locations
  - Event information

## 🚀 API Endpoints

### Main Endpoint: Sync & Scrape All

```
GET /api/admin/sync-and-scrape-all?force_rescrape=false&max_concurrent=5
```

**Parameters:**
- `force_rescrape` (default: false): If true, scrape all URLs even if no new links detected
- `max_concurrent` (default: 5): Maximum concurrent scraping operations (1-10)

**Response:**
```json
{
  "ok": true,
  "success": true,
  "categories_found": 6,
  "total_urls": 26,
  "new_categories": ["secret_places"],
  "updated_categories": ["tourist_spots"],
  "unchanged_categories": ["accommodation_hotels", "restaurants_food", "scams", "dangerous_areas"],
  "saved_categories": ["secret_places", "tourist_spots"],
  "scraping_performed": true,
  "scraping_results": {
    "total_urls_attempted": 26,
    "total_urls_scraped": 22,
    "success_rate": 84.62,
    "by_category": {
      "accommodation_hotels": 5,
      "tourist_spots": 8,
      "restaurants_food": 4,
      "scams": 3,
      "dangerous_areas": 2
    }
  },
  "message": "1 new category/categories, 1 updated category/categories, 4 unchanged category/categories, scraped 22/26 URLs"
}
```

### Check Category Summary

```
GET /api/admin/category-summary
```

**Response:**
```json
{
  "ok": true,
  "success": true,
  "categories": {
    "accommodation_hotels": {
      "urls_count": 8,
      "scraped_items_count": 7,
      "last_updated": "2026-02-07T10:30:00",
      "content_hash": "abc123..."
    },
    "tourist_spots": {
      "urls_count": 10,
      "scraped_items_count": 9,
      "last_updated": "2026-02-07T10:35:00",
      "content_hash": "def456..."
    }
  },
  "total_categories": 6,
  "total_urls": 26,
  "total_scraped_items": 22
}
```

## 📊 Data Structure

### Scraped Content (per URL)

Each scraped item contains:

```json
{
  "url": "https://example.com",
  "category": "accommodation_hotels",
  "title": "Hotel Name",
  "description": "Rich description from website",
  "content_text": "Full article content...",
  "images": ["https://example.com/image1.jpg", ...],
  "places_mentioned": ["Bacolod City", "Lacson Street"],
  "location": {
    "address": "123 Main St, Bacolod City",
    "latitude": 10.6407,
    "longitude": 122.9689,
    "city": "Bacolod City",
    "region": "Negros Occidental"
  },
  "events": [
    {
      "name": "MassKara Festival",
      "start_date": "2026-10-01",
      "end_date": "2026-10-31",
      "location": "Bacolod City",
      "description": "Annual Festival of Smiles"
    }
  ],
  "personality_keywords": {
    "adventurous": 0.3,
    "cultural": 0.8,
    "foodie": 0.2,
    "nature_lover": 0.1,
    "history_buff": 0.7,
    "social": 0.6
  },
  "domain": "example.com",
  "scraped_at": "2026-02-07T10:30:00"
}
```

## 🎯 Recommendation Integration

The recommendation system:

1. **Loads scraped content by category** when generating recommendations
2. **Matches items** using multiple criteria:
   - Name similarity (flexible matching)
   - Location proximity (if user location provided)
   - Personality keyword alignment
   - Event dates (if user has travel dates)
3. **Enhances recommendations** with:
   - Images from scraped websites
   - Rich descriptions from scraped content
   - Accurate location data
   - Event information
   - Links to original websites

### Example Flow

```
User requests recommendations
  ↓
Load user profile (personality traits)
  ↓
For each category (hotels, restaurants, etc.):
  ↓
  Load scraped content for that category
  ↓
  Get base recommendations from recommendation engine
  ↓
  Match each recommendation with scraped content:
    - Check name similarity
    - Check location proximity
    - Check personality alignment
  ↓
  Enhance recommendation with:
    - Image from scraped content
    - Description from scraped content
    - Location from scraped content
    - Events from scraped content
  ↓
Return enhanced recommendations
```

## 🔄 Update Detection

The system uses `content_hash` to detect changes:

1. **Hash Calculation**: Creates SHA256 hash of sorted URLs per category
2. **Comparison**: Compares current hash with stored hash
3. **Update Logic**:
   - If hash differs → New links detected → Update category → Scrape
   - If hash matches → No changes → Skip scraping (unless `force_rescrape=true`)

This ensures:
- ✅ Only scrapes when new links are added
- ✅ Avoids unnecessary re-scraping
- ✅ Efficient resource usage

## 📝 Usage Examples

### Initial Setup (First Time)

```bash
# Scrape all URLs from Google Sheet
curl "http://localhost:8000/api/admin/sync-and-scrape-all?force_rescrape=true"
```

### Regular Updates (When Sheet Changes)

```bash
# Automatically detects new links and scrapes only if needed
curl "http://localhost:8000/api/admin/sync-and-scrape-all"
```

### Check Status

```bash
# See summary of all categories
curl "http://localhost:8000/api/admin/category-summary"
```

## 🎨 Frontend Integration

The frontend can:

1. **Display category workspaces** showing:
   - Number of URLs per category
   - Number of scraped items
   - Last update time

2. **Show recommendations** enhanced with:
   - Images from scraped websites
   - Rich descriptions
   - Accurate locations
   - Event information

3. **Trigger updates** when admin adds new links to sheet

## ✅ Benefits

1. **Organized Data**: Each category is a separate workspace
2. **Efficient Updates**: Only scrapes when new links detected
3. **Rich Content**: Extracts structured data (locations, events, images)
4. **Personality-Aligned**: Uses personality keywords for better matching
5. **Comprehensive**: Scrapes ALL URLs, not just validated ones
6. **Smart Routing**: Uses appropriate scraper for each site type

## 🔍 Monitoring

Check logs for:
- `✨ New category detected` - New category added to sheet
- `🔄 Category updated` - New links added to existing category
- `✅ Scraping completed` - Scraping finished with statistics
- `Loaded X scraped content items` - Recommendations loading scraped data
- `Enhancing item with scraped content` - Recommendations being enhanced
