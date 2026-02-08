"""Bright Data integration using Dataset Snapshot API pattern."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import random
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class BrightDataClient:
    """Async wrapper around Bright Data's Dataset Snapshot API.

    Uses the Dataset Snapshot pattern:
    1. Trigger a dataset operation via /datasets/v3/trigger
    2. Poll /datasets/v3/progress/{snapshot_id} until ready
    3. Download results via /datasets/v3/snapshot/{snapshot_id}

    For Google/Bing searches, uses the /request endpoint with zone "ai_agent".
    """

    def __init__(self) -> None:
        self._api_key = (settings.bright_data_api_key or "").strip()
        self._base_url = settings.bright_data_base_url.rstrip("/")
        self._reddit_search_dataset_id = settings.bright_data_reddit_search_dataset_id
        self._reddit_comments_dataset_id = settings.bright_data_reddit_comments_dataset_id
        self._timeout = settings.bright_data_timeout_seconds
        self._poll_max_attempts = settings.bright_data_snapshot_poll_max_attempts
        self._poll_delay = settings.bright_data_snapshot_poll_delay
        # Use configured zone or fallback to common zones
        self._zone = settings.bright_data_zone or "ai_agent"  # Use configured zone first
        # Web Unlocker zone for browser automation (like Apify actors)
        self._web_unlocker_zone = settings.bright_data_web_unlocker_zone or "web_unlocker"
        # SERP API zone and key for Google/Bing searches
        self._serp_zone = settings.bright_data_serp_zone or "serp_api2"
        self._serp_api_key = (settings.bright_data_serp_api_key or self._api_key).strip()  # Fallback to main API key

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    async def search_public(
        self,
        source: str,
        query: str,
        *,
        limit: int = 8,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a Bright Data search job for a specific source.

        For Google/Bing: Uses /request endpoint with zone "ai_agent"
        For Reddit: Uses dataset trigger with Reddit search dataset
        For Facebook: Falls back to mock (no dataset available in sample)
        """
        if source.lower() == "reddit":
            return await self._reddit_search_via_dataset(query, limit=limit)
        elif source.lower() in ("google", "bing"):
            return await self._serp_search_via_request(source, query, limit=limit)
        elif source.lower() == "facebook":
            # Facebook doesn't have a dataset in the sample, fallback to mock
            logger.warning("Facebook search not implemented via dataset API, using mock")
            return self._mock_response("search", {"source": "facebook", "query": query, "limit": limit})
        else:
            logger.warning(f"Unknown source '{source}', using mock")
            return self._mock_response("search", {"source": source, "query": query, "limit": limit})

    async def fetch_person_details(
        self,
        email: str,
        full_name: str,
        *,
        handles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Download enriched personal details and comments.

        Note: No dataset provided in sample code for person details.
        Falls back to mock data for now.
        """
        logger.warning("Person details dataset not configured, using mock")
        return self._mock_response(
            "person-details",
            {"email": email, "full_name": full_name, "handles": handles or []},
        )

    async def fetch_reddit_comments(
        self,
        urls: List[str],
        *,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Retrieve Reddit comments for the supplied URLs using dataset API."""
        if not urls:
            return {"success": True, "comments": {}}

        return await self._reddit_comments_via_dataset(urls, days_back=10, comment_limit=str(limit))

    async def scrape_with_web_unlocker(
        self,
        url: str,
        *,
        wait_for: Optional[int] = 5000,
        render: bool = True,
    ) -> Optional[str]:
        """Scrape a URL using Bright Data Web Unlocker API (browser automation like Apify).
        
        This uses browser automation to execute JavaScript and handle dynamic content,
        making it suitable for scraping JavaScript-heavy sites like Facebook/Instagram.
        
        Args:
            url: The URL to scrape
            wait_for: Milliseconds to wait for page to load (default: 5000)
            render: Whether to render JavaScript (default: True)
            
        Returns:
            HTML content as string, or None if scraping failed
        """
        if not self._api_key:
            logger.warning("Bright Data API key not configured, cannot use Web Unlocker")
            return None
        
        request_url = f"{self._base_url}/request"
        
        # Try configured Web Unlocker zone first, then fallback zones
        zones_to_try = [self._web_unlocker_zone, "web_unlocker", "webscrape_amzn"]
        zones_to_try = [z for z in zones_to_try if z and z != self._zone]  # Remove empty and duplicate zones
        
        last_error = None
        
        for zone in zones_to_try:
            payload = {
                "zone": zone,
                "url": url,
                "format": "raw",  # Get raw HTML
            }
            
            # Add browser automation options
            if render:
                payload["render"] = "html"  # Render JavaScript
            if wait_for:
                payload["wait_for"] = wait_for
            
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }
            
            try:
                logger.info(f"🌐 Using Bright Data Web Unlocker (zone: {zone}) to scrape: {url[:80]}...")
                async with httpx.AsyncClient(timeout=self._timeout * 3) as client:  # Longer timeout for browser automation
                    response = await client.post(request_url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    # Web Unlocker returns HTML content
                    html_content = response.text
                    
                    if html_content and len(html_content) > 100:  # Basic validation
                        logger.info(f"✅ Successfully scraped {len(html_content)} characters using Web Unlocker zone '{zone}'")
                        return html_content
                    else:
                        logger.warning(f"Zone '{zone}' returned empty/invalid content, trying next zone...")
                        continue
                        
            except httpx.HTTPStatusError as exc:
                error_detail = ""
                try:
                    error_detail = exc.response.text[:200]
                except:
                    pass
                
                # Provide more helpful error messages for 404
                if exc.response.status_code == 404:
                    logger.warning(
                        f"Web Unlocker zone '{zone}' returned 404 Not Found. "
                        f"This zone doesn't exist or isn't accessible. "
                        f"Check your Bright Data dashboard for correct zone names."
                    )
                else:
                    logger.warning(f"Web Unlocker zone '{zone}' returned {exc.response.status_code}: {error_detail}")
                last_error = exc
                continue
            except Exception as exc:
                logger.warning(f"Web Unlocker zone '{zone}' failed: {exc}")
                last_error = exc
                continue
        
        if last_error:
            logger.error(f"All Web Unlocker zones failed. Last error: {last_error}")
        else:
            logger.warning("No Web Unlocker zones available or all returned empty content")
        
        return None

    # --------------------------------------------------------------------- #
    # Internal helpers - Dataset Snapshot API
    # --------------------------------------------------------------------- #
    async def _reddit_search_via_dataset(
        self,
        keyword: str,
        *,
        limit: int = 75,
        date: str = "All time",
        sort_by: str = "Hot",
    ) -> Dict[str, Any]:
        """Search Reddit using dataset trigger pattern."""
        if not self._api_key:
            return self._mock_response("search", {"source": "reddit", "query": keyword, "limit": limit})

        trigger_url = f"{self._base_url}/datasets/v3/trigger"
        params = {
            "dataset_id": self._reddit_search_dataset_id,
            "include_errors": "true",
            "type": "discover_new",
            "discover_by": "keyword",
        }
        data = [
            {
                "keyword": keyword,
                "date": date,
                "sort_by": sort_by,
                "num_of_posts": limit,
            }
        ]

        try:
            snapshot_data = await self._trigger_and_download_snapshot(
                trigger_url, params, data, operation_name="reddit_search"
            )
            if not snapshot_data:
                return self._mock_response("search", {"source": "reddit", "query": keyword, "limit": limit})

            # Transform to expected format
            results = []
            for post in snapshot_data[:limit]:
                results.append(
                    {
                        "title": post.get("title", ""),
                        "url": post.get("url", ""),
                        "snippet": post.get("title", ""),  # Use title as snippet
                        "platform": "reddit",
                        "comments": [],  # Comments come from separate dataset
                    }
                )

            return {
                "success": True,
                "source": "reddit",
                "query": keyword,
                "results": results,
            }
        except Exception as exc:
            logger.warning(f"Reddit search via dataset failed: {exc}, falling back to mock")
            return self._mock_response("search", {"source": "reddit", "query": keyword, "limit": limit})

    async def _reddit_comments_via_dataset(
        self,
        urls: List[str],
        *,
        days_back: int = 10,
        load_all_replies: bool = False,
        comment_limit: str = "",
    ) -> Dict[str, Any]:
        """Retrieve Reddit comments using dataset trigger pattern."""
        if not self._api_key:
            return self._mock_response("reddit-comments", {"urls": urls, "limit": len(urls) * 10})

        trigger_url = f"{self._base_url}/datasets/v3/trigger"
        params = {
            "dataset_id": self._reddit_comments_dataset_id,
            "include_errors": "true",
        }
        data = [
            {
                "url": url,
                "days_back": days_back,
                "load_all_replies": load_all_replies,
                "comment_limit": comment_limit,
            }
            for url in urls
        ]

        try:
            snapshot_data = await self._trigger_and_download_snapshot(
                trigger_url, params, data, operation_name="reddit_comments"
            )
            if not snapshot_data:
                return self._mock_response("reddit-comments", {"urls": urls, "limit": len(urls) * 10})

            # Transform to expected format: {url: [comment_texts]}
            comments_by_url: Dict[str, List[str]] = {}
            for comment in snapshot_data:
                url = comment.get("url", "")
                content = comment.get("comment", "")
                if url and content:
                    if url not in comments_by_url:
                        comments_by_url[url] = []
                    comments_by_url[url].append(content)

            return {
                "success": True,
                "comments": comments_by_url,
            }
        except Exception as exc:
            logger.warning(f"Reddit comments via dataset failed: {exc}, falling back to mock")
            return self._mock_response("reddit-comments", {"urls": urls, "limit": len(urls) * 10})

    def _extract_organic_from_serp_response(self, data: Any) -> List[Dict[str, Any]]:
        """Extract and normalize organic results from Bright Data / generic SERP JSON.

        Bright Data brd_json=1 can return keys like general, input, navigation, images, top_ads.
        Organic results may be under 'organic', 'organic_results', or 'results' (items may have type='organic').
        Items may use 'link' instead of 'url' and 'description' instead of 'snippet'.
        """
        if not isinstance(data, dict):
            return []
        out: List[Dict[str, Any]] = []

        def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
            title = item.get("title", "")
            url = item.get("url") or item.get("link", "")
            snippet = item.get("snippet") or item.get("description", "")
            return {"title": title, "url": url, "snippet": snippet}

        # Try known keys in order
        for key in ("organic", "organic_results", "results"):
            cand = data.get(key)
            if not isinstance(cand, list):
                continue
            out = []
            for item in cand:
                if not isinstance(item, dict):
                    continue
                # Bright Data 'results' can have {"type":"organic", ...}; skip non-organic if type present
                if key == "results" and item.get("type") not in (None, "organic"):
                    continue
                n = normalize_item(item)
                if n.get("url") or n.get("title"):
                    out.append(n)
            if out:
                return out

        # Bright Data full schema may put organic under another key; scan any list of dicts with link/url+title
        for v in data.values():
            if not isinstance(v, list) or not v:
                continue
            try:
                first = v[0]
                if not isinstance(first, dict):
                    continue
                if ("link" in first or "url" in first) and ("title" in first or "description" in first):
                    out = []
                    for item in v:
                        if isinstance(item, dict):
                            n = normalize_item(item)
                            if n.get("url") or n.get("title"):
                                out.append(n)
                    if out:
                        return out
            except (IndexError, TypeError):
                pass

        # Nested under "data" or "general" (Bright Data brd_json=1 uses general, input, navigation, images, top_ads)
        for nest_key in ("data", "general"):
            nested = data.get(nest_key) if isinstance(data, dict) else None
            if isinstance(nested, dict):
                rec = self._extract_organic_from_serp_response(nested)
                if rec:
                    return rec
        return []

    async def _serp_search_via_request(
        self,
        engine: str,
        query: str,
        *,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search Google/Bing using /request endpoint with SERP API (serp_api2 zone) for structured JSON results."""
        # Use SERP API key if available, otherwise fallback to main API key
        api_key = self._serp_api_key or self._api_key
        if not api_key:
            logger.warning(f"Bright Data API key not configured, returning mock data for {engine} search")
            return self._mock_response("search", {"source": engine, "query": query, "limit": limit})

        if engine.lower() == "google":
            base_url = "https://www.google.com/search"
        elif engine.lower() == "bing":
            base_url = "https://www.bing.com/search"
        else:
            logger.warning(f"Unknown engine '{engine}', using mock")
            return self._mock_response("search", {"source": engine, "query": query, "limit": limit})

        url = f"{self._base_url}/request"
        
        # Try SERP zone first (serp_api2); use format=json + brd_json=1 for structured results (verified by test_serp_api.py)
        zones_to_try = [self._serp_zone, "serp_api2", self._zone, "ai_agent", "webscrape_amzn"]
        zones_to_try = [z for z in zones_to_try if z and z != self._serp_zone]  # Remove empty and duplicate zones
        zones_to_try.insert(0, self._serp_zone)  # Put SERP zone first
        
        last_error = None
        full_response = None
        
        for zone in zones_to_try:
            # For serp_api2 / SERP zone: use format=json and &brd_json=1 (returns structured JSON)
            # For other zones: use format=raw (HTML)
            is_serp_zone = (zone or "").lower() in ("serp_api2", (self._serp_zone or "").lower())
            if is_serp_zone:
                search_url = f"{base_url}?q={quote_plus(query)}&brd_json=1"
                fmt = "json"
            else:
                search_url = f"{base_url}?q={quote_plus(query)}"
                fmt = "raw"
            
            payload: Dict[str, Any] = {
                "zone": zone,
                "url": search_url,
                "format": fmt
            }
            # Bright Data: parsed_light returns {"organic": [{link, title, description}, ...]} (top 10, faster)
            if is_serp_zone:
                payload["data_format"] = "parsed_light"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            try:
                logger.info(f"Trying Bright Data zone '{zone}' (format={fmt}) for {engine} search: {query[:50]}...")
                async with httpx.AsyncClient(timeout=self._timeout * 2) as client:  # Longer timeout for SERP
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    
                    # Check if response is JSON (some zones return JSON even with raw format)
                    content_type = response.headers.get('content-type', '').lower()
                    is_json_response = 'json' in content_type or response.text.strip().startswith('{')
                    
                    if is_json_response:
                        # SERP API returns JSON with nested structure
                        json_response = response.json()
                        logger.debug(f"Zone '{zone}' JSON response keys: {list(json_response.keys())}")
                        
                        # The body field contains the actual search results as a JSON string
                        if "body" in json_response and isinstance(json_response["body"], str):
                            import json as json_lib
                            try:
                                body_data = json_lib.loads(json_response["body"])
                                full_response = body_data
                                logger.info(f"✅ Parsed body JSON - keys: {list(body_data.keys()) if isinstance(body_data, dict) else 'not a dict'}")
                                # Log if organic key exists
                                if isinstance(body_data, dict) and "organic" in body_data:
                                    logger.info(f"✅ Found 'organic' key in body with {len(body_data.get('organic', []))} items")
                            except json_lib.JSONDecodeError as e:
                                logger.warning(f"Failed to parse body as JSON: {e}")
                                full_response = json_response
                        elif "body" in json_response and isinstance(json_response["body"], dict):
                            # Body is already a dict
                            full_response = json_response["body"]
                            logger.info(f"✅ Body is already dict - keys: {list(full_response.keys()) if isinstance(full_response, dict) else 'not a dict'}")
                        else:
                            full_response = json_response
                            logger.info(f"✅ Using full JSON response - keys: {list(full_response.keys()) if isinstance(full_response, dict) else 'not a dict'}")
                    else:
                        # Raw format - returns HTML, need to parse it
                        html_content = response.text
                        logger.debug(f"Zone '{zone}' returned HTML (length: {len(html_content)} chars)")
                        
                        # Try to extract search results from HTML
                        # Google search results use specific structures
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            results = []
                            
                            # Method 1: Modern Google results - div.g or div with data-ved attribute
                            result_divs = soup.find_all('div', class_=lambda x: x and 'g' in x.split() if x else False)
                            if not result_divs:
                                # Try divs with data-ved (Google result identifier)
                                result_divs = soup.find_all('div', attrs={'data-ved': True})
                            
                            if result_divs:
                                for div in result_divs[:limit]:
                                    # Extract title from h3 tag
                                    h3 = div.find('h3')
                                    title = h3.get_text(strip=True) if h3 else ''
                                    
                                    # Extract URL from anchor tag
                                    link = div.find('a', href=True)
                                    url = ''
                                    if link:
                                        href = link.get('href', '')
                                        # Google uses /url?q= for redirects
                                        if href.startswith('/url?q='):
                                            import urllib.parse
                                            url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q', [''])[0]
                                        elif href.startswith('http'):
                                            url = href
                                    
                                    # Extract snippet
                                    snippet = ''
                                    # Try multiple snippet selectors
                                    snippet_selectors = [
                                        'span[style*="-webkit-line-clamp"]',
                                        'div[style*="-webkit-line-clamp"]',
                                        '.VwiC3b',  # Google snippet class
                                        'span:not([class*="icon"])',  # Generic span
                                    ]
                                    for selector in snippet_selectors:
                                        snippet_elem = div.select_one(selector)
                                        if snippet_elem:
                                            snippet = snippet_elem.get_text(strip=True)[:300]
                                            break
                                    
                                    # If no snippet found, try getting text from div excluding title
                                    if not snippet:
                                        all_text = div.get_text(separator=' ', strip=True)
                                        if title:
                                            snippet = all_text.replace(title, '', 1).strip()[:300]
                                        else:
                                            snippet = all_text[:300]
                                    
                                    if title and url:
                                        results.append({
                                            "title": title,
                                            "url": url,
                                            "snippet": snippet,
                                            "description": snippet
                                        })
                            
                            # Method 2: Fallback - find all h3 titles with links nearby
                            if not results:
                                h3_tags = soup.find_all('h3')
                                for h3 in h3_tags[:limit]:
                                    title = h3.get_text(strip=True)
                                    if not title:
                                        continue
                                    
                                    # Find link near this h3
                                    parent = h3.parent
                                    link = None
                                    if parent:
                                        link = parent.find('a', href=True)
                                    if not link:
                                        # Try next sibling
                                        next_elem = h3.find_next_sibling()
                                        if next_elem:
                                            link = next_elem.find('a', href=True)
                                    
                                    if link:
                                        href = link.get('href', '')
                                        # Handle Google redirect URLs
                                        if href.startswith('/url?q='):
                                            import urllib.parse
                                            url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q', [''])[0]
                                        elif href.startswith('http'):
                                            url = href
                                        else:
                                            url = f"https://www.google.com{href}" if href.startswith('/') else href
                                        
                                        # Get snippet from surrounding text
                                        snippet = ''
                                        if parent:
                                            snippet = parent.get_text(separator=' ', strip=True).replace(title, '', 1).strip()[:300]
                                        
                                        if url:
                                            results.append({
                                                "title": title,
                                                "url": url,
                                                "snippet": snippet,
                                                "description": snippet
                                            })
                            
                            # Method 3: Last resort - extract from any links with meaningful text
                            if not results:
                                links = soup.find_all('a', href=True)
                                seen_urls = set()
                                for link in links:
                                    href = link.get('href', '')
                                    title = link.get_text(strip=True)
                                    
                                    # Skip navigation and non-result links
                                    if not title or len(title) < 10:
                                        continue
                                    if any(skip in href.lower() for skip in ['/search?', '/maps', '/images', '/settings', '/preferences']):
                                        continue
                                    
                                    # Handle Google redirect URLs
                                    if href.startswith('/url?q='):
                                        import urllib.parse
                                        url = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q', [''])[0]
                                    elif href.startswith('http'):
                                        url = href
                                    else:
                                        continue
                                    
                                    if url and url not in seen_urls and 'google.com' not in url:
                                        seen_urls.add(url)
                                        results.append({
                                            "title": title[:200],
                                            "url": url,
                                            "snippet": "",
                                            "description": ""
                                        })
                                        if len(results) >= limit:
                                            break
                            
                            if results:
                                logger.info(f"✅ Parsed {len(results)} results from HTML using zone '{zone}'")
                                full_response = {"organic": results}
                            else:
                                # Log HTML structure for debugging
                                logger.warning(f"Zone '{zone}' returned HTML but no results found in structure")
                                logger.debug(f"HTML sample (first 2000 chars): {html_content[:2000]}")
                                # Try to find any h3 or links for debugging
                                h3_count = len(soup.find_all('h3'))
                                link_count = len(soup.find_all('a', href=True))
                                logger.debug(f"Found {h3_count} h3 tags and {link_count} links in HTML")
                                continue
                                
                        except ImportError:
                            logger.warning("BeautifulSoup not available, cannot parse HTML. Install: pip install beautifulsoup4")
                            continue
                        except Exception as parse_error:
                            logger.warning(f"Failed to parse HTML response: {parse_error}")
                            logger.debug(f"HTML preview: {html_content[:500]}")
                            continue
                    
                    # Check if we got valid results - try Bright Data SERP and common field names
                    organic = self._extract_organic_from_serp_response(full_response)
                    
                    if organic:
                        logger.info(f"✅ Successfully got {len(organic)} results using zone '{zone}'")
                        break
                    else:
                        logger.warning(f"Zone '{zone}' returned empty results (response keys: {list(full_response.keys()) if isinstance(full_response, dict) else 'not a dict'}), trying next zone...")
                        continue
                        
            except httpx.HTTPStatusError as exc:
                error_detail = ""
                try:
                    error_detail = exc.response.text[:200]
                except:
                    pass
                
                # Provide more helpful error messages for 404
                if exc.response.status_code == 404:
                    logger.warning(
                        f"Zone '{zone}' returned 404 Not Found. "
                        f"This zone doesn't exist or isn't accessible in your Bright Data account. "
                        f"Please check your Bright Data dashboard to verify zone names. "
                        f"Error detail: {error_detail}"
                    )
                else:
                    logger.warning(f"Zone '{zone}' returned {exc.response.status_code}: {error_detail}")
                last_error = exc
                continue
            except Exception as exc:
                logger.warning(f"Zone '{zone}' failed: {exc}")
                last_error = exc
                continue
        
        # If we got a successful response, process it
        if full_response:
            try:
                # Extract organic from Bright Data / generic SERP shape and normalize
                organic = self._extract_organic_from_serp_response(full_response)[:limit]
                knowledge = full_response.get("knowledge", {}) if isinstance(full_response, dict) else {}

                results = []
                for idx, item in enumerate(organic):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", item.get("link", "")),
                            "snippet": item.get("snippet", item.get("description", "")),
                            "platform": engine.lower(),
                            "comments": [],
                        }
                    )

                # Add knowledge graph data if available
                if knowledge and results:
                    knowledge_snippet = f"Knowledge: {knowledge.get('title', '')} - {knowledge.get('description', '')}"
                    if knowledge_snippet.strip() != "Knowledge:  - ":
                        results[0]["snippet"] = knowledge_snippet + "\n" + results[0]["snippet"]

                return {
                    "success": True,
                    "source": engine.lower(),
                    "query": query,
                    "results": results,
                }
            except Exception as exc:
                logger.error(f"Error processing Bright Data response: {exc}")
        
        # All zones failed or returned empty results
        if last_error:
            error_msg = str(last_error)
            if "404" in error_msg or "Not Found" in error_msg:
                logger.error(
                    f"All zones failed for {engine} search with 404 errors. "
                    f"This means the zones don't exist in your Bright Data account.\n"
                    f"   ACTION REQUIRED:\n"
                    f"   1. Log into Bright Data dashboard: https://brightdata.com/\n"
                    f"   2. Go to Zones section and check available zones\n"
                    f"   3. Update your .env file with correct zone names:\n"
                    f"      - BRIGHT_DATA_SERP_ZONE=your_actual_serp_zone\n"
                    f"      - BRIGHT_DATA_ZONE=your_actual_residential_zone\n"
                    f"   4. Verify your API keys have access to these zones\n"
                    f"   5. See BRIGHT_DATA_ZONE_404_FIX.md for detailed troubleshooting"
                )
            else:
                logger.error(f"All zones failed for {engine} search. Last error: {last_error}")
        else:
            logger.warning(f"No zones available or all returned empty results for {engine} search")
            logger.warning(f"   This might mean:")
            logger.warning(f"   1. The zones are not configured in your Bright Data account")
            logger.warning(f"   2. The zones don't have access to SERP API")
            logger.warning(f"   3. The API key doesn't have permissions for these zones")
            logger.warning(f"   4. The query format needs adjustment")
        
        # Return empty results instead of mock to indicate failure
        logger.warning(f"Returning empty results for {engine} search (query: {query[:50]}...)")
        return {
            "success": True,  # API call succeeded, just no results
            "source": engine.lower(),
            "query": query,
            "results": [],
            "error": "All SERP zones returned empty results. Check Bright Data zone configuration."
        }

    async def _trigger_and_download_snapshot(
        self,
        trigger_url: str,
        params: Dict[str, Any],
        data: List[Dict[str, Any]],
        operation_name: str = "operation",
    ) -> Optional[List[Dict[str, Any]]]:
        """Trigger a dataset snapshot, poll until ready, then download."""
        if not self._api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            # Step 1: Trigger the snapshot
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(trigger_url, params=params, json=data, headers=headers)
                response.raise_for_status()
                trigger_result = response.json()

            snapshot_id = trigger_result.get("snapshot_id")
            if not snapshot_id:
                logger.error(f"{operation_name}: No snapshot_id in trigger response")
                return None

            logger.info(f"{operation_name}: Triggered snapshot {snapshot_id}")

            # Step 2: Poll until ready
            if not await self._poll_snapshot_status(snapshot_id, operation_name):
                logger.error(f"{operation_name}: Snapshot {snapshot_id} did not complete")
                return None

            # Step 3: Download the snapshot
            return await self._download_snapshot(snapshot_id, operation_name)

        except httpx.HTTPStatusError as exc:
            logger.warning(f"{operation_name}: HTTP {exc.response.status_code} - {exc}")
            return None
        except Exception as exc:
            logger.warning(f"{operation_name}: Failed - {exc}")
            return None

    async def _poll_snapshot_status(
        self,
        snapshot_id: str,
        operation_name: str = "operation",
    ) -> bool:
        """Poll snapshot status until ready or timeout."""
        progress_url = f"{self._base_url}/datasets/v3/progress/{snapshot_id}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        for attempt in range(self._poll_max_attempts):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(progress_url, headers=headers)
                    response.raise_for_status()
                    progress_data = response.json()

                status = progress_data.get("status")
                if status == "ready":
                    logger.info(f"{operation_name}: Snapshot {snapshot_id} completed")
                    return True
                elif status == "failed":
                    logger.error(f"{operation_name}: Snapshot {snapshot_id} failed")
                    return False
                elif status == "running":
                    if attempt % 5 == 0:  # Log every 5th attempt
                        logger.debug(f"{operation_name}: Snapshot {snapshot_id} still processing...")
                    await asyncio.sleep(self._poll_delay)
                else:
                    logger.warning(f"{operation_name}: Unknown status '{status}' for {snapshot_id}")
                    await asyncio.sleep(self._poll_delay)

            except Exception as exc:
                logger.warning(f"{operation_name}: Error polling status: {exc}")
                await asyncio.sleep(self._poll_delay)

        logger.error(f"{operation_name}: Timeout waiting for snapshot {snapshot_id}")
        return False

    async def _download_snapshot(
        self,
        snapshot_id: str,
        operation_name: str = "operation",
        format: str = "json",
    ) -> Optional[List[Dict[str, Any]]]:
        """Download completed snapshot data."""
        download_url = f"{self._base_url}/datasets/v3/snapshot/{snapshot_id}?format={format}"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self._timeout * 2) as client:
                response = await client.get(download_url, headers=headers)
                response.raise_for_status()
                data = response.json()

            if isinstance(data, list):
                logger.info(f"{operation_name}: Downloaded {len(data)} items from snapshot {snapshot_id}")
            else:
                logger.info(f"{operation_name}: Downloaded snapshot {snapshot_id}")
                data = [data] if data else []

            return data
        except Exception as exc:
            logger.error(f"{operation_name}: Error downloading snapshot {snapshot_id}: {exc}")
            return None

    # ------------------------------------------------------------------ #
    # Mock data generation
    # ------------------------------------------------------------------ #
    def _mock_response(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic mock data for development and tests."""
        seed_source = f"{endpoint}:{payload}".encode("utf-8", "ignore")
        seed = int(hashlib.sha256(seed_source).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)

        if endpoint == "search":
            source = payload.get("source", "unknown").lower()
            query = payload.get("query", "")
            limit = payload.get("limit", 5)
            return {
                "success": True,
                "source": source,
                "query": query,
                "results": [
                    {
                        "title": f"{source.title()} insight {idx+1}",
                        "url": f"https://{source}.example.com/{idx}",
                        "snippet": f"Synthesized snippet about {query} ({source} #{idx+1}).",
                        "platform": source,
                        "comments": [
                            f"Comment {c+1} about {query} from {source} feed."
                            for c in range(rng.randint(2, 4))
                        ],
                    }
                    for idx in range(limit)
                ],
            }

        if endpoint == "person-details":
            full_name = payload.get("full_name") or "Unknown"
            handles = payload.get("handles") or []
            dominant_theme = " ".join(handles[:1]) if handles else full_name.split()[0]
            return {
                "success": True,
                "full_name": full_name,
                "email": payload.get("email"),
                "bio": f"{full_name} is known for a passion for {dominant_theme or 'travel'} adventures.",
                "locations": [
                    {"city": "Bacolod", "country": "Philippines"},
                    {"city": "Silay", "country": "Philippines"},
                ],
                "public_comments": [
                    f"{full_name} shared excitement about discovering hidden cafes.",
                    f"Friends describe {full_name.split()[0]} as a planner who still loves spontaneous road trips.",
                ],
                "social_handles": handles,
            }

        if endpoint == "reddit-comments":
            urls = payload.get("urls", [])
            comment_limit = payload.get("limit", 20)
            return {
                "success": True,
                "comments": {
                    url: [
                        f"Reddit insight {idx+1} for {url} focusing on local experiences."
                        for idx in range(min(comment_limit // len(urls) if urls else comment_limit, 6))
                    ]
                    for url in urls
                },
            }

        # Default mock
        return {
            "success": True,
            "source": endpoint,
            "payload": payload,
        }


# Global instance reused throughout the application.
bright_data_client = BrightDataClient()
