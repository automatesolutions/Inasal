"""
Event extraction from HTML/text content.
Extracts event names, dates, locations from various sources.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from bs4 import BeautifulSoup
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class EventExtractor:
    """Extract event information from HTML content"""

    def __init__(self):
        self.event_keywords = [
            "festival", "event", "celebration", "fair", "exhibition",
            "concert", "show", "performance", "competition", "tournament",
            "workshop", "seminar", "conference", "meetup", "gathering"
        ]
        self.month_names = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]

    def extract_events(self, html: str, text_content: str = "") -> List[Dict[str, Any]]:
        """
        Extract event information from HTML and text.
        Returns list of event objects: [{name, start_date, end_date, location, description}]
        """
        soup = BeautifulSoup(html, "html.parser") if html else None
        text = text_content or (soup.get_text() if soup else "")
        
        events = []
        
        # Try JSON-LD Event schema first (most reliable)
        if soup:
            json_ld_events = self._extract_from_json_ld(soup)
            events.extend(json_ld_events)
        
        # Extract from text patterns
        text_events = self._extract_from_text(text)
        events.extend(text_events)
        
        # Deduplicate events (by name and date)
        unique_events = []
        seen = set()
        for event in events:
            key = (event.get("name", "").lower(), event.get("start_date"))
            if key not in seen and event.get("name"):
                seen.add(key)
                unique_events.append(event)
        
        return unique_events[:10]  # Limit to 10 events

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract events from JSON-LD structured data"""
        events = []
        json_scripts = soup.find_all("script", {"type": "application/ld+json"})
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    if item.get("@type") == "Event":
                        event = {}
                        
                        # Name
                        if item.get("name"):
                            event["name"] = item["name"]
                        
                        # Dates
                        if item.get("startDate"):
                            event["start_date"] = self._parse_date(item["startDate"])
                        if item.get("endDate"):
                            event["end_date"] = self._parse_date(item["endDate"])
                        elif event.get("start_date"):
                            # If only start date, assume 1-day event
                            event["end_date"] = event["start_date"]
                        
                        # Location
                        if item.get("location"):
                            loc = item["location"]
                            if isinstance(loc, dict):
                                if loc.get("name"):
                                    event["location"] = loc["name"]
                                elif loc.get("address"):
                                    if isinstance(loc["address"], dict):
                                        event["location"] = loc["address"].get("addressLocality") or loc["address"].get("streetAddress")
                                    else:
                                        event["location"] = loc["address"]
                            elif isinstance(loc, str):
                                event["location"] = loc
                        
                        # Description
                        if item.get("description"):
                            event["description"] = item["description"][:500]
                        
                        if event.get("name"):
                            events.append(event)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Error parsing JSON-LD Event: {e}")
                continue
        
        return events

    def _extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract events from text using patterns"""
        events = []
        
        # Pattern 1: "Event Name on/at Date"
        pattern1 = r'([A-Z][^.!?]*?(?:' + '|'.join(self.event_keywords) + r')[^.!?]*?)\s+(?:on|at|from|during)\s+([^.!?]+?)(?:\.|,|$)'
        matches = re.finditer(pattern1, text, re.IGNORECASE)
        for match in matches:
            event_name = match.group(1).strip()
            date_str = match.group(2).strip()
            
            dates = self._parse_date_range(date_str)
            if dates:
                events.append({
                    "name": event_name,
                    "start_date": dates.get("start"),
                    "end_date": dates.get("end"),
                    "description": f"Found in content: {date_str}"
                })
        
        # Pattern 2: "Date - Event Name" or "Event Name - Date"
        pattern2 = r'((?:' + '|'.join(self.month_names) + r')\s+\d{1,2}(?:-\d{1,2})?(?:,\s*\d{4})?)\s*[-–]\s*([A-Z][^.!?]+)'
        matches = re.finditer(pattern2, text, re.IGNORECASE)
        for match in matches:
            date_str = match.group(1).strip()
            event_name = match.group(2).strip()
            
            dates = self._parse_date_range(date_str)
            if dates:
                events.append({
                    "name": event_name,
                    "start_date": dates.get("start"),
                    "end_date": dates.get("end"),
                    "description": f"Found in content: {date_str}"
                })
        
        # Pattern 3: Common Bacolod events (MassKara Festival, etc.)
        bacolod_events = {
            "masskara festival": {"month": 10, "description": "Annual Festival of Smiles"},
            "masskara": {"month": 10, "description": "Festival of Smiles"},
        }
        
        for event_key, event_info in bacolod_events.items():
            if event_key in text.lower():
                # Try to find year
                year_match = re.search(r'\b(20\d{2})\b', text)
                year = int(year_match.group(1)) if year_match else datetime.now().year
                
                events.append({
                    "name": event_key.title(),
                    "start_date": f"{year}-{event_info['month']:02d}-01",
                    "end_date": f"{year}-{event_info['month']:02d}-31",
                    "description": event_info["description"],
                    "location": "Bacolod City"
                })
        
        return events

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse a date string to ISO format"""
        if not date_str:
            return None
        
        try:
            # Try dateutil parser first
            dt = date_parser.parse(date_str, fuzzy=True)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            # Try manual parsing
            return self._parse_date_manual(date_str)

    def _parse_date_manual(self, date_str: str) -> Optional[str]:
        """Manual date parsing for common patterns"""
        date_str = date_str.strip()
        
        # Pattern: "October 2024" or "October 2025"
        month_year = re.match(r'(' + '|'.join(self.month_names) + r')\s+(\d{4})', date_str, re.IGNORECASE)
        if month_year:
            month_name = month_year.group(1).lower()
            year = int(month_year.group(2))
            month_num = self.month_names.index(month_name) + 1
            return f"{year}-{month_num:02d}-01"
        
        # Pattern: "March 15-20, 2024"
        range_match = re.match(r'(' + '|'.join(self.month_names) + r')\s+(\d{1,2})-(\d{1,2}),\s*(\d{4})', date_str, re.IGNORECASE)
        if range_match:
            month_name = range_match.group(1).lower()
            start_day = int(range_match.group(2))
            year = int(range_match.group(4))
            month_num = self.month_names.index(month_name) + 1
            return f"{year}-{month_num:02d}-{start_day:02d}"
        
        # Pattern: "Every Sunday" or "Every first Sunday"
        if "every" in date_str.lower() and "sunday" in date_str.lower():
            # Return next Sunday
            today = datetime.now()
            days_ahead = 6 - today.weekday()  # Sunday is 6
            if days_ahead <= 0:
                days_ahead += 7
            next_sunday = today + timedelta(days=days_ahead)
            return next_sunday.strftime("%Y-%m-%d")
        
        return None

    def _parse_date_range(self, date_str: str) -> Optional[Dict[str, Optional[str]]]:
        """Parse a date range string"""
        date_str = date_str.strip()
        
        # Pattern: "March 15-20, 2024"
        range_match = re.match(r'(' + '|'.join(self.month_names) + r')\s+(\d{1,2})-(\d{1,2}),\s*(\d{4})', date_str, re.IGNORECASE)
        if range_match:
            month_name = range_match.group(1).lower()
            start_day = int(range_match.group(2))
            end_day = int(range_match.group(3))
            year = int(range_match.group(4))
            month_num = self.month_names.index(month_name) + 1
            
            return {
                "start": f"{year}-{month_num:02d}-{start_day:02d}",
                "end": f"{year}-{month_num:02d}-{end_day:02d}"
            }
        
        # Pattern: "October 2024" (entire month)
        month_year = re.match(r'(' + '|'.join(self.month_names) + r')\s+(\d{4})', date_str, re.IGNORECASE)
        if month_year:
            month_name = month_year.group(1).lower()
            year = int(month_year.group(2))
            month_num = self.month_names.index(month_name) + 1
            
            # Get last day of month
            if month_num == 12:
                last_day = 31
            elif month_num in [4, 6, 9, 11]:
                last_day = 30
            else:
                last_day = 29 if year % 4 == 0 else 28
            
            return {
                "start": f"{year}-{month_num:02d}-01",
                "end": f"{year}-{month_num:02d}-{last_day:02d}"
            }
        
        # Single date
        single_date = self._parse_date(date_str)
        if single_date:
            return {
                "start": single_date,
                "end": single_date
            }
        
        return None
