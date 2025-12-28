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

    async def _serp_search_via_request(
        self,
        engine: str,
        query: str,
        *,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Search Google/Bing using /request endpoint with zone 'ai_agent'."""
        if not self._api_key:
            return self._mock_response("search", {"source": engine, "query": query, "limit": limit})

        if engine.lower() == "google":
            base_url = "https://www.google.com/search"
        elif engine.lower() == "bing":
            base_url = "https://www.bing.com/search"
        else:
            logger.warning(f"Unknown engine '{engine}', using mock")
            return self._mock_response("search", {"source": engine, "query": query, "limit": limit})

        url = f"{self._base_url}/request"
        payload = {
            "zone": "ai_agent",
            "url": f"{base_url}?q={quote_plus(query)}&brd_json=1",
            "format": "raw",
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                full_response = response.json()

                # Extract and transform to expected format
                organic = full_response.get("organic", [])[:limit]
                knowledge = full_response.get("knowledge", {})

                results = []
                for idx, item in enumerate(organic):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("description", ""),
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
        except httpx.HTTPStatusError as exc:
            logger.warning(
                f"SERP search ({engine}) returned {exc.response.status_code}, falling back to mock"
            )
            return self._mock_response("search", {"source": engine, "query": query, "limit": limit})
        except Exception as exc:
            logger.warning(f"SERP search ({engine}) failed: {exc}, falling back to mock")
            return self._mock_response("search", {"source": engine, "query": query, "limit": limit})

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
