"""
Admin routes: Google Sheet sync to InstantDB (Bacolod Details).
"""

import logging
from fastapi import APIRouter, HTTPException, Query

from app.instantdb_client import instantdb_client
from app.sheets_sync import (
    fetch_and_parse_sheet,
    content_hash,
    check_urls_from_sheet,
    scrape_all_urls_from_sheet,
)
from app.services.batch_scraper import BatchScraper
from app.services.sheet_scraping_service import SheetScrapingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/sync-sheet")
async def sync_sheet_to_instantdb(
    validate_links: bool = Query(
        True,
        description="Check each URL from the sheet (HEAD/GET); only working links are saved. Set to false to sync all links without checking.",
    ),
    scrape_content: bool = Query(
        False,
        description="Scrape content from all URLs and save to InstantDB. This may take several minutes.",
    ),
):
    """
    Fetch Bacolod Details Google Sheet, check links (optional), sync URLs to InstantDB,
    and optionally scrape content from all URLs.
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    try:
        categories = await fetch_and_parse_sheet()
        if not categories:
            return {
                "ok": False,
                "message": "No data from sheet (check sheet is shared as 'Anyone with link can view')",
                "categories": {},
            }
        if validate_links:
            valid_categories, broken_by_category = await check_urls_from_sheet(categories)
        else:
            valid_categories = categories
            broken_by_category = {}
        
        # If scraping is requested, save ALL URLs (not just validated) to InstantDB
        # This ensures all URLs are available for scraping and future use
        categories_to_save = categories if scrape_content else valid_categories
        
        existing = await instantdb_client.get_all_curated_resources()
        updated = []
        for slug, urls in categories_to_save.items():
            if not urls:
                continue
            current_hash = content_hash({slug: urls})
            existing_doc = existing.get(slug)
            existing_hash = existing_doc.get("content_hash") if existing_doc else None
            if existing_hash != current_hash:
                ok = await instantdb_client.save_curated_category(
                    slug, urls, content_hash=current_hash
                )
                if ok:
                    updated.append(slug)
        
        # Scrape content if requested - use ALL URLs from sheet (not just validated ones)
        scraped_summary = None
        if scrape_content:
            logger.info("Starting content scraping from ALL sheet URLs (including unvalidated)...")
            # Use original categories (all URLs) for scraping, not just validated ones
            scraped_by_category = await scrape_all_urls_from_sheet(categories)
            total_scraped = sum(len(v) for v in scraped_by_category.values())
            total_attempted = sum(len(v) for v in categories.values())
            scraped_summary = {
                "total_urls_attempted": total_attempted,
                "total_urls_scraped": total_scraped,
                "by_category": {k: len(v) for k, v in scraped_by_category.items() if v},
            }
            logger.info(f"Scraped content from {total_scraped}/{total_attempted} URLs")
        
        total_broken = sum(len(v) for v in broken_by_category.values())
        msg = f"Synced {len(updated)} categories"
        if validate_links and total_broken:
            msg += f"; {total_broken} broken link(s) from sheet were not saved"
        elif validate_links:
            msg += " (all checked links are valid)"
        if scrape_content and scraped_summary:
            msg += f"; scraped content from {scraped_summary['total_urls_scraped']}/{scraped_summary['total_urls_attempted']} URLs"
        
        return {
            "ok": True,
            "message": msg,
            "categories": list(valid_categories.keys()),
            "updated": updated,
            "broken_links": {k: v for k, v in broken_by_category.items() if v} or None,
            "scraped_content": scraped_summary,
        }
    except Exception as e:
        logger.exception("Sheet sync failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scrape-sheet-content")
async def scrape_sheet_content(
    use_instantdb: bool = Query(
        False,
        description="If true, scrape URLs already in InstantDB. If false, fetch fresh from Google Sheet and scrape ALL URLs.",
    ),
):
    """
    Scrape content from URLs and save to InstantDB.
    
    - If use_instantdb=false (default): Fetches fresh from Google Sheet and scrapes ALL URLs (even if link validation would fail)
    - If use_instantdb=true: Scrapes URLs already stored in InstantDB (from previous sync)
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    try:
        if use_instantdb:
            # Get URLs from InstantDB (already synced)
            existing = await instantdb_client.get_all_curated_resources()
            if not existing:
                return {
                    "ok": False,
                    "message": "No URLs found in InstantDB. Run /sync-sheet first, or use use_instantdb=false to fetch from sheet.",
                }
            
            # Build categories dict from InstantDB
            categories = {
                slug: doc.get("urls", [])
                for slug, doc in existing.items()
                if doc.get("urls")
            }
            logger.info(f"Scraping content from {sum(len(v) for v in categories.values())} URLs in InstantDB...")
        else:
            # Fetch fresh from Google Sheet - get ALL URLs
            categories = await fetch_and_parse_sheet()
            if not categories:
                return {
                    "ok": False,
                    "message": "No data from sheet (check sheet is shared as 'Anyone with link can view')",
                }
            logger.info(f"Fetched {sum(len(v) for v in categories.values())} URLs from Google Sheet, scraping all...")
        
        scraped_by_category = await scrape_all_urls_from_sheet(categories)
        total_scraped = sum(len(v) for v in scraped_by_category.values())
        total_attempted = sum(len(v) for v in categories.values())
        
        return {
            "ok": True,
            "message": f"Scraped content from {total_scraped}/{total_attempted} URLs",
            "total_urls_attempted": total_attempted,
            "total_urls_scraped": total_scraped,
            "scraped_by_category": {k: len(v) for k, v in scraped_by_category.items() if v},
        }
    except Exception as e:
        logger.exception("Content scraping failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-scrape")
async def batch_scrape(
    use_existing_urls: bool = Query(
        False,
        description="If true, use URLs from InstantDB. If false, fetch fresh from Google Sheet.",
    ),
    max_concurrent: int = Query(
        5,
        ge=1,
        le=10,
        description="Maximum concurrent scraping operations (1-10).",
    ),
):
    """
    Batch scrape all URLs with progress tracking, retry logic, and incremental saves.
    Uses the BatchScraper service for better orchestration and error handling.
    
    Returns progress information and summary of scraping results.
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    
    try:
        batch_scraper = BatchScraper(max_retries=2, retry_delay=5.0)
        
        result = await batch_scraper.scrape_all_from_sheet(
            use_existing_urls=use_existing_urls,
            max_concurrent=max_concurrent,
        )
        
        return {
            "ok": result.get("success", False),
            "message": result.get("error") or f"Batch scraping completed: {result.get('total_scraped', 0)}/{result.get('total_urls', 0)} URLs scraped",
            "total_urls": result.get("total_urls", 0),
            "total_scraped": result.get("total_scraped", 0),
            "scraped_by_category": result.get("scraped_by_category", {}),
            "progress": result.get("progress", {}),
        }
    except Exception as e:
        logger.exception("Batch scraping failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch-scrape-progress")
async def get_batch_scrape_progress():
    """
    Get current progress of batch scraping operation.
    Returns None if no batch scraping is in progress.
    """
    try:
        batch_scraper = BatchScraper()
        progress = batch_scraper.get_progress()
        
        if progress:
            return {
                "ok": True,
                "progress": progress,
            }
        else:
            return {
                "ok": False,
                "message": "No batch scraping in progress",
            }
    except Exception as e:
        logger.exception("Error getting batch scrape progress")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-scraped-content")
async def check_scraped_content():
    """
    Diagnostic endpoint to check if scraping has been executed and what data exists.
    Returns information about scraped content in InstantDB.
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    
    try:
        # Get all scraped content
        all_scraped = await instantdb_client.get_all_scraped_content()
        
        # Also try direct query to verify
        import asyncio
        await asyncio.sleep(2)  # Wait a bit for InstantDB propagation
        
        # Get curated URLs for comparison
        curated = await instantdb_client.get_all_curated_resources()
        
        # Count URLs by category
        curated_urls_by_category = {}
        for slug, doc in curated.items():
            urls = doc.get("urls", [])
            curated_urls_by_category[slug] = len(urls) if urls else 0
        
        # Count scraped content by category
        scraped_by_category = {}
        sample_items = {}
        total_items = 0
        
        # Also try querying each category individually
        test_categories = ["tourist_spots", "accommodation_hotels", "restaurants_food", "secret_places", "scams", "dangerous_areas"]
        for category in test_categories:
            items = await instantdb_client.get_scraped_content_by_category(category)
            if items:
                scraped_by_category[category] = len(items)
                total_items += len(items)
                if category not in sample_items and items:
                    sample = items[0]
                    sample_items[category] = {
                        "url": sample.get("url", "N/A")[:100],
                        "title": sample.get("title", "N/A")[:100],
                        "has_description": bool(sample.get("description")),
                        "has_images": bool(sample.get("images")),
                        "has_location": bool(sample.get("location")),
                        "has_events": bool(sample.get("events")),
                        "has_personality_keywords": bool(sample.get("personality_keywords")),
                    }
        
        # Also include items from all_scraped
        for category, items in all_scraped.items():
            if category not in scraped_by_category:
                scraped_by_category[category] = len(items)
                total_items += len(items)
            if items and category not in sample_items:
                sample = items[0]
                sample_items[category] = {
                    "url": sample.get("url", "N/A")[:100],
                    "title": sample.get("title", "N/A")[:100],
                    "has_description": bool(sample.get("description")),
                    "has_images": bool(sample.get("images")),
                    "has_location": bool(sample.get("location")),
                    "has_events": bool(sample.get("events")),
                    "has_personality_keywords": bool(sample.get("personality_keywords")),
                }
        
        return {
            "ok": True,
            "curated_urls_by_category": curated_urls_by_category,
            "scraped_content_by_category": scraped_by_category,
            "total_scraped_items": total_items,
            "sample_items": sample_items,
            "message": f"Found {total_items} scraped items across {len(scraped_by_category)} categories",
        }
    except Exception as e:
        logger.exception("Error checking scraped content")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-and-scrape-all")
async def sync_and_scrape_all(
    force_rescrape: bool = Query(
        False,
        description="If true, scrape all URLs even if no new links detected. If false, only scrape when new links are added.",
    ),
    max_concurrent: int = Query(
        5,
        ge=1,
        le=10,
        description="Maximum concurrent scraping operations (1-10).",
    ),
):
    """
    Comprehensive endpoint: Sync Google Sheet, detect new links, and scrape all URLs.
    
    This endpoint:
    1. Fetches ALL URLs from Google Sheet
    2. Organizes them by category (Accommodation & Hotels, Tourist Spots, etc.)
    3. Detects new links using content hash comparison
    4. Scrapes ALL URLs and saves to InstantDB (organized by category)
    5. Updates only when new links are detected (unless force_rescrape=true)
    
    Categories:
    - accommodation_hotels: Accommodation & Hotels
    - tourist_spots: Tourist Spots & Hidden Gems
    - restaurants_food: Restaurants & Food
    - dangerous_areas: Dangerous Areas & Travel Warnings
    - scams: Scams to Watch Out For
    - secret_places: Secret Places in Bacolod
    
    Returns detailed results including which categories were updated and scraping statistics.
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    
    try:
        service = SheetScrapingService()
        result = await service.sync_and_scrape_all(
            force_rescrape=force_rescrape,
            max_concurrent=max_concurrent,
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error"),
            )
        
        return {
            "ok": True,
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Sync and scrape failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/category-summary")
async def get_category_summary():
    """
    Get summary of all categories: URLs count, scraped items count, last update time.
    Shows the current state of each category workspace.
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    
    try:
        service = SheetScrapingService()
        result = await service.get_category_summary()
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Unknown error"),
            )
        
        return {
            "ok": True,
            **result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting category summary")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-instantdb-data")
async def verify_instantdb_data():
    """
    Direct verification of InstantDB data storage.
    Queries InstantDB directly to verify scraped content is stored.
    """
    if not instantdb_client._is_available():
        raise HTTPException(
            status_code=503,
            detail="InstantDB not configured (INSTANTDB_APP_ID / INSTANTDB_ADMIN_TOKEN)",
        )
    
    try:
        import asyncio
        
        # Wait a moment for any recent writes to propagate
        await asyncio.sleep(3)
        
        # Direct query to InstantDB for all category-specific collections
        headers = instantdb_client._get_headers()
        url = f"{instantdb_client.base_url}/admin/query"
        
        # Query all category-specific collections
        category_collections = [
            "scraped_content_accommodation_hotels",
            "scraped_content_tourist_spots",
            "scraped_content_restaurants_food",
            "scraped_content_dangerous_areas",
            "scraped_content_scams",
            "scraped_content_secret_places",
        ]
        
        query_dict = {}
        for collection in category_collections:
            query_dict[collection] = {}
        
        payload = {"query": query_dict}
        
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                return {
                    "ok": False,
                    "error": f"Query failed: {response.status_code}",
                    "response": response.text[:500],
                }
            
            data = response.json()
            
            # Group by category from category-specific collections
            by_category = {}
            category_map = {
                "scraped_content_accommodation_hotels": "accommodation_hotels",
                "scraped_content_tourist_spots": "tourist_spots",
                "scraped_content_restaurants_food": "restaurants_food",
                "scraped_content_dangerous_areas": "dangerous_areas",
                "scraped_content_scams": "scams",
                "scraped_content_secret_places": "secret_places",
            }
            
            all_items = []
            for collection_name, category_slug in category_map.items():
                items = data.get(collection_name) or []
                if items:
                    by_category[category_slug] = items
                    all_items.extend(items)
            
            items = all_items
            
            # Get sample items
            sample_items = {}
            for cat, items_list in list(by_category.items())[:6]:  # First 6 categories
                if items_list:
                    sample = items_list[0]
                    sample_items[cat] = {
                        "id": sample.get("id"),
                        "url": sample.get("url", "N/A")[:80],
                        "title": sample.get("title", "N/A")[:80],
                        "category": sample.get("category"),
                        "has_description": bool(sample.get("description")),
                        "has_images": len(sample.get("images", [])) > 0,
                        "has_location": bool(sample.get("location")),
                        "has_events": len(sample.get("events", [])) > 0,
                        "has_personality_keywords": bool(sample.get("personality_keywords")),
                        "scraped_at": sample.get("scraped_at"),
                    }
            
            return {
                "ok": True,
                "total_items_in_db": len(items),
                "categories_found": list(by_category.keys()),
                "items_by_category": {cat: len(items_list) for cat, items_list in by_category.items()},
                "sample_items": sample_items,
                "raw_query_response_keys": list(data.keys()),
                "message": f"Found {len(items)} items in InstantDB across {len(by_category)} categories",
            }
            
    except Exception as e:
        logger.exception("Error verifying InstantDB data")
        return {
            "ok": False,
            "error": str(e),
        }
