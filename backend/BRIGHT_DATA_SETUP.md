# Bright Data Web Unlocker Setup Guide

## Current Issue
Getting **401 Unauthorized** errors when trying to use Web Unlocker.

## What We Need From You

Please provide the following information from your Bright Data dashboard:

### 1. **Web Unlocker Zone Name**
- Go to: https://brightdata.com/dashboard
- Navigate to **"Zones"** or **"Web Unlocker"** section
- Find your Web Unlocker zone name (e.g., `web_unlocker`, `browser_automation`, etc.)
- **This is different from your regular proxy zone** (`webscrape_amzn`)

### 2. **API Key Verification**
- Your current API key: `eb2ca709644144656034d231530b20b5a27eff44306808843c78a12019fee95b`
- Verify this API key has access to Web Unlocker in your Bright Data dashboard
- Check if Web Unlocker is enabled for your account

### 3. **API Endpoint**
- Web Unlocker typically uses: `https://api.brightdata.com/request`
- But some accounts might use a different endpoint
- Check your Bright Data dashboard for the correct endpoint

## Current Configuration

In your `.env` file, we have:
```
BRIGHT_DATA_API_KEY=eb2ca709644144656034d231530b20b5a27eff44306808843c78a12019fee95b
BRIGHT_DATA_WEB_UNLOCKER_ZONE=web_unlocker
```

## Next Steps

1. **Check your Bright Data dashboard** for:
   - Web Unlocker zone name
   - Verify API key has Web Unlocker access
   - Check if Web Unlocker is enabled/activated

2. **Update `.env` file** with the correct zone name:
   ```
   BRIGHT_DATA_WEB_UNLOCKER_ZONE=your_actual_zone_name_here
   ```

3. **Alternative**: If Web Unlocker isn't available, we can try:
   - Using Bright Data's Residential Proxy with browser automation
   - Using Bright Data's Dataset API for Facebook (if available)
   - Using Facebook Graph API (requires authentication)

## Testing

Once you provide the zone name, we'll test it with:
```bash
python backend/test_bright_data_zones.py
```
