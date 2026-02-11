"""
Batch scraping orchestration service.
Handles progress tracking, retry logic, and incremental InstantDB saves.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

from app.sheets_sync import scrape_all_urls_from_sheet, fetch_and_parse_sheet
from app.instantdb_client import instantdb_client

logger = logging.getLogger(__name__)


@dataclass
class ScrapingProgress:
    """Track progress of batch scraping"""
    total_urls: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    category_progress: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        elapsed = None
        if self.start_time:
            end = self.end_time or datetime.utcnow()
            elapsed = (end - self.start_time).total_seconds()
        
        return {
            "total_urls": self.total_urls,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "progress_percent": round((self.completed / self.total_urls * 100) if self.total_urls > 0 else 0, 2),
            "elapsed_seconds": elapsed,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "errors": self.errors[:10],  # Limit to last 10 errors
            "category_progress": self.category_progress,
        }


class BatchScraper:
    """Orchestrate batch scraping with progress tracking and retry logic"""
    
    def __init__(self, max_retries: int = 2, retry_delay: float = 5.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress: Optional[ScrapingProgress] = None
    
    async def scrape_all_from_sheet(
        self,
        use_existing_urls: bool = False,
        max_concurrent: int = 5,
        progress_callback: Optional[Callable[[ScrapingProgress], None]] = None,
    ) -> Dict[str, Any]:
        """
        Scrape all URLs from Google Sheet or InstantDB.
        
        Args:
            use_existing_urls: If True, use URLs from InstantDB; if False, fetch from Google Sheet
            max_concurrent: Maximum concurrent scraping operations
            progress_callback: Optional callback function to report progress
        
        Returns:
            Dictionary with scraping results and summary
        """
        self.progress = ScrapingProgress()
        self.progress.start_time = datetime.utcnow()
        
        try:
            # Get URLs to scrape
            if use_existing_urls:
                logger.info("Using URLs from InstantDB")
                categories = await self._get_urls_from_instantdb()
            else:
                logger.info("Fetching URLs from Google Sheet")
                categories = await fetch_and_parse_sheet()
            
            if not categories:
                self.progress.end_time = datetime.utcnow()
                return {
                    "success": False,
                    "error": "No URLs found to scrape",
                    "progress": self.progress.to_dict(),
                }
            
            # Calculate total URLs
            self.progress.total_urls = sum(len(urls) for urls in categories.values())
            logger.info(f"Found {self.progress.total_urls} URLs across {len(categories)} categories")
            
            # Initialize category progress tracking
            for category in categories:
                self.progress.category_progress[category] = {
                    "total": len(categories[category]),
                    "completed": 0,
                    "failed": 0,
                }
            
            # Scrape with retry logic
            scraped_by_category = await self._scrape_with_retries(
                categories,
                max_concurrent=max_concurrent,
                progress_callback=progress_callback,
            )
            
            self.progress.end_time = datetime.utcnow()
            
            # Calculate summary
            total_scraped = sum(len(v) for v in scraped_by_category.values())
            self.progress.completed = total_scraped
            self.progress.failed = self.progress.total_urls - total_scraped
            
            return {
                "success": True,
                "scraped_by_category": {
                    cat: len(items) for cat, items in scraped_by_category.items()
                },
                "total_scraped": total_scraped,
                "total_urls": self.progress.total_urls,
                "progress": self.progress.to_dict(),
            }
            
        except Exception as e:
            logger.error(f"Batch scraping failed: {e}", exc_info=True)
            self.progress.end_time = datetime.utcnow()
            self.progress.errors.append(str(e))
            
            return {
                "success": False,
                "error": str(e),
                "progress": self.progress.to_dict(),
            }
    
    async def _get_urls_from_instantdb(self) -> Dict[str, List[str]]:
        """Get URLs from InstantDB curated resources"""
        try:
            curated = await instantdb_client.get_all_curated_resources()
            categories = {}
            for category_slug, data in curated.items():
                if isinstance(data, dict) and "urls" in data:
                    categories[category_slug] = data["urls"]
                elif isinstance(data, list):
                    categories[category_slug] = data
            return categories
        except Exception as e:
            logger.error(f"Failed to get URLs from InstantDB: {e}")
            return {}
    
    async def _scrape_with_retries(
        self,
        categories: Dict[str, List[str]],
        max_concurrent: int = 5,
        progress_callback: Optional[Callable[[ScrapingProgress], None]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape URLs with retry logic and progress tracking.
        Saves to InstantDB incrementally (not all at once).
        """
        scraped_by_category: Dict[str, List[Dict[str, Any]]] = {}
        
        # Initialize categories
        for category in categories:
            scraped_by_category[category] = []
        
        # Scrape URLs with retries
        for category, urls in categories.items():
            for url in urls:
                success = False
                last_error = None
                
                for attempt in range(self.max_retries + 1):
                    try:
                        # Use the smart router from sheets_sync
                        from app.sheets_sync import _should_use_scrapy
                        from app.content_scraper import ContentScraper
                        from app.scrapers.scrapy_runner import ScrapyRunner
                        
                        use_scrapy = _should_use_scrapy(url)
                        
                        if use_scrapy:
                            scrapy_runner = ScrapyRunner()
                            content = await scrapy_runner.run_spider(url, category)
                        else:
                            scraper = ContentScraper()
                            content = await scraper.scrape_url(url, category)
                        
                        if content:
                            # Save to InstantDB incrementally
                            saved = await instantdb_client.save_scraped_content(url, content)
                            if saved:
                                scraped_by_category[category].append(content)
                                self.progress.completed += 1
                                self.progress.category_progress[category]["completed"] += 1
                                success = True
                                break
                        
                    except Exception as e:
                        last_error = str(e)
                        logger.warning(f"Attempt {attempt + 1} failed for {url[:60]}...: {e}")
                        
                        if attempt < self.max_retries:
                            await asyncio.sleep(self.retry_delay)
                    
                    # Update progress
                    if progress_callback:
                        progress_callback(self.progress)
                
                if not success:
                    self.progress.failed += 1
                    self.progress.category_progress[category]["failed"] += 1
                    if last_error:
                        self.progress.errors.append(f"{url[:60]}...: {last_error}")
                    logger.error(f"Failed to scrape {url[:60]}... after {self.max_retries + 1} attempts")
        
        return scraped_by_category
    
    def get_progress(self) -> Optional[Dict[str, Any]]:
        """Get current scraping progress"""
        if self.progress:
            return self.progress.to_dict()
        return None
