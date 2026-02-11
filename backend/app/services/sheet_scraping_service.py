"""
Comprehensive Google Sheet scraping service.
Scrapes ALL URLs from Google Sheet, organizes by category, and updates only when new links are added.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.sheets_sync import (
    fetch_and_parse_sheet,
    content_hash,
    scrape_all_urls_from_sheet,
)
from app.instantdb_client import instantdb_client

logger = logging.getLogger(__name__)


class SheetScrapingService:
    """
    Service to scrape all URLs from Google Sheet, organize by category,
    and update only when new links are detected.
    """

    # Category mapping: Sheet headers -> Internal slugs
    CATEGORY_MAPPING = {
        "accommodation and hotels": "accommodation_hotels",
        "accomodation and hotels": "accommodation_hotels",  # typo variant
        "tourist spots & hidden gems": "tourist_spots",
        "tourist spots and hidden gems": "tourist_spots",
        "restaurants & food": "restaurants_food",
        "restaurants and food": "restaurants_food",
        "dangerous areas & travel warnings": "dangerous_areas",
        "dangerous areas and travel warnings": "dangerous_areas",
        "scams to watch out for": "scams",
        "secret places in bacolod": "secret_places",
    }

    async def sync_and_scrape_all(
        self,
        force_rescrape: bool = False,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Main entry point: Sync Google Sheet, detect new links, and scrape all URLs.
        
        Args:
            force_rescrape: If True, scrape all URLs even if no new links detected
            max_concurrent: Maximum concurrent scraping operations
        
        Returns:
            Dictionary with sync and scraping results
        """
        if not instantdb_client._is_available():
            return {
                "success": False,
                "error": "InstantDB not configured",
            }

        try:
            # Step 1: Fetch and parse Google Sheet
            logger.info("📥 Fetching Google Sheet...")
            categories = await fetch_and_parse_sheet()
            
            if not categories:
                return {
                    "success": False,
                    "error": "No data from sheet (check sheet is shared as 'Anyone with link can view')",
                }

            total_urls = sum(len(urls) for urls in categories.values())
            logger.info(f"📊 Found {total_urls} URLs across {len(categories)} categories")

            # Step 2: Check for new links using content_hash
            logger.info("🔍 Checking for new links...")
            existing = await instantdb_client.get_all_curated_resources()
            
            new_categories = []
            updated_categories = []
            unchanged_categories = []
            
            for slug, urls in categories.items():
                if not urls:
                    continue
                
                current_hash = content_hash({slug: urls})
                existing_doc = existing.get(slug)
                existing_hash = existing_doc.get("content_hash") if existing_doc else None
                
                if existing_hash is None:
                    # New category
                    new_categories.append(slug)
                    logger.info(f"  ✨ New category detected: {slug} ({len(urls)} URLs)")
                elif existing_hash != current_hash:
                    # Category updated (new links added)
                    updated_categories.append(slug)
                    existing_urls = existing_doc.get("urls", [])
                    new_urls = [u for u in urls if u not in existing_urls]
                    logger.info(f"  🔄 Category updated: {slug} ({len(new_urls)} new URLs)")
                else:
                    # No changes
                    unchanged_categories.append(slug)

            # Step 3: Save updated categories to InstantDB
            saved_categories = []
            for slug in new_categories + updated_categories:
                urls = categories[slug]
                current_hash = content_hash({slug: urls})
                ok = await instantdb_client.save_curated_category(
                    slug, urls, content_hash=current_hash
                )
                if ok:
                    saved_categories.append(slug)

            # Step 4: Scrape all URLs (if new links detected or force_rescrape)
            should_scrape = force_rescrape or (len(new_categories) > 0 or len(updated_categories) > 0)
            
            scraping_results = None
            if should_scrape:
                logger.info("🚀 Starting scraping of ALL URLs...")
                logger.info(f"   Categories to scrape: {len(categories)}")
                logger.info(f"   Total URLs: {total_urls}")
                
                scraped_by_category = await scrape_all_urls_from_sheet(
                    categories, max_concurrent=max_concurrent
                )
                
                total_scraped = sum(len(v) for v in scraped_by_category.values())
                scraping_results = {
                    "total_urls_attempted": total_urls,
                    "total_urls_scraped": total_scraped,
                    "success_rate": round((total_scraped / total_urls * 100) if total_urls > 0 else 0, 2),
                    "by_category": {
                        cat: len(items) 
                        for cat, items in scraped_by_category.items() 
                        if items
                    },
                }
                
                logger.info(f"✅ Scraping completed: {total_scraped}/{total_urls} URLs ({scraping_results['success_rate']}%)")
            else:
                logger.info("⏭️  No new links detected. Skipping scraping.")
                logger.info(f"   Unchanged categories: {len(unchanged_categories)}")

            return {
                "success": True,
                "categories_found": len(categories),
                "total_urls": total_urls,
                "new_categories": new_categories,
                "updated_categories": updated_categories,
                "unchanged_categories": unchanged_categories,
                "saved_categories": saved_categories,
                "scraping_performed": should_scrape,
                "scraping_results": scraping_results,
                "message": self._generate_summary_message(
                    new_categories, updated_categories, unchanged_categories, scraping_results
                ),
            }

        except Exception as e:
            logger.exception("Error in sync_and_scrape_all")
            return {
                "success": False,
                "error": str(e),
            }

    def _generate_summary_message(
        self,
        new_categories: List[str],
        updated_categories: List[str],
        unchanged_categories: List[str],
        scraping_results: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a human-readable summary message"""
        parts = []
        
        if new_categories:
            parts.append(f"{len(new_categories)} new category/categories")
        if updated_categories:
            parts.append(f"{len(updated_categories)} updated category/categories")
        if unchanged_categories:
            parts.append(f"{len(unchanged_categories)} unchanged category/categories")
        
        if scraping_results:
            parts.append(
                f"scraped {scraping_results['total_urls_scraped']}/{scraping_results['total_urls_attempted']} URLs"
            )
        elif not new_categories and not updated_categories:
            parts.append("no changes detected - scraping skipped")
        
        return ", ".join(parts)

    async def get_category_summary(self) -> Dict[str, Any]:
        """
        Get summary of all categories: URLs count, scraped items count, last update time.
        """
        if not instantdb_client._is_available():
            return {"error": "InstantDB not configured"}

        try:
            # Get curated URLs
            curated = await instantdb_client.get_all_curated_resources()
            
            # Get scraped content
            all_scraped = await instantdb_client.get_all_scraped_content()
            
            summary = {}
            for slug, doc in curated.items():
                urls = doc.get("urls", [])
                scraped_items = all_scraped.get(slug, [])
                
                summary[slug] = {
                    "urls_count": len(urls) if urls else 0,
                    "scraped_items_count": len(scraped_items),
                    "last_updated": doc.get("updated_at"),
                    "content_hash": doc.get("content_hash"),
                }
            
            return {
                "success": True,
                "categories": summary,
                "total_categories": len(summary),
                "total_urls": sum(c["urls_count"] for c in summary.values()),
                "total_scraped_items": sum(c["scraped_items_count"] for c in summary.values()),
            }

        except Exception as e:
            logger.exception("Error getting category summary")
            return {
                "success": False,
                "error": str(e),
            }
