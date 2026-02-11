"""
Location extraction from HTML/text content.
Extracts addresses, coordinates, and location information from various sources.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class LocationExtractor:
    """Extract location information from HTML content"""

    def __init__(self):
        self.bacolod_keywords = [
            "bacolod", "negros occidental", "negros", "visayas",
            "lacson", "ruins", "masskara", "mambukal", "campuestohan"
        ]

    def extract_location(self, html: str, url: str, text_content: str = "") -> Optional[Dict[str, Any]]:
        """
        Extract location information from HTML and text.
        Returns structured location object: {address, latitude, longitude, city, region}
        """
        soup = BeautifulSoup(html, "html.parser") if html else None
        
        location = {}
        
        # Try meta tags first
        if soup:
            location = self._extract_from_meta_tags(soup) or {}
        
        # Try JSON-LD structured data
        if soup and not location.get("latitude"):
            json_ld_location = self._extract_from_json_ld(soup)
            if json_ld_location:
                location.update(json_ld_location)
        
        # Try Google Maps embeds
        if soup and not location.get("latitude"):
            maps_location = self._extract_from_google_maps(soup, html)
            if maps_location:
                location.update(maps_location)
        
        # Extract from text patterns
        if not location.get("address"):
            text_location = self._extract_from_text(text_content or (soup.get_text() if soup else ""))
            if text_location:
                location.update(text_location)
        
        # Extract coordinates from text
        if not location.get("latitude"):
            coords = self._extract_coordinates_from_text(text_content or (soup.get_text() if soup else ""))
            if coords:
                location["latitude"] = coords.get("latitude")
                location["longitude"] = coords.get("longitude")
        
        # Extract address from text if not found
        if not location.get("address"):
            address = self._extract_address_from_text(text_content or (soup.get_text() if soup else ""))
            if address:
                location["address"] = address
        
        # Normalize city/region
        if location.get("address") or location.get("city"):
            city_region = self._extract_city_region(location.get("address") or location.get("city") or "")
            if city_region:
                location["city"] = city_region.get("city") or "Bacolod City"
                location["region"] = city_region.get("region") or "Negros Occidental"
        
        # Return None if no location data found
        if not location or (not location.get("address") and not location.get("latitude")):
            return None
        
        return {
            "address": location.get("address"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "city": location.get("city") or "Bacolod City",
            "region": location.get("region") or "Negros Occidental",
        }

    def _extract_from_meta_tags(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract location from meta tags"""
        location = {}
        
        # Geo coordinates
        lat_tag = soup.find("meta", {"property": "geo:latitude"}) or soup.find("meta", {"name": "geo:latitude"})
        lng_tag = soup.find("meta", {"property": "geo:longitude"}) or soup.find("meta", {"name": "geo:longitude"})
        
        if lat_tag and lng_tag:
            try:
                location["latitude"] = float(lat_tag.get("content", ""))
                location["longitude"] = float(lng_tag.get("content", ""))
            except (ValueError, TypeError):
                pass
        
        # Place location
        place_location = soup.find("meta", {"property": "place:location:latitude"})
        if place_location:
            try:
                location["latitude"] = float(place_location.get("content", ""))
                lng_tag = soup.find("meta", {"property": "place:location:longitude"})
                if lng_tag:
                    location["longitude"] = float(lng_tag.get("content", ""))
            except (ValueError, TypeError):
                pass
        
        # Address
        address_tag = soup.find("meta", {"property": "business:contact_data:street_address"}) or \
                     soup.find("meta", {"property": "og:street_address"}) or \
                     soup.find("meta", {"name": "address"})
        if address_tag:
            location["address"] = address_tag.get("content", "").strip()
        
        # Locality/City
        locality_tag = soup.find("meta", {"property": "business:contact_data:locality"}) or \
                      soup.find("meta", {"property": "og:locality"})
        if locality_tag:
            location["city"] = locality_tag.get("content", "").strip()
        
        # Region
        region_tag = soup.find("meta", {"property": "business:contact_data:region"}) or \
                    soup.find("meta", {"property": "og:region"})
        if region_tag:
            location["region"] = region_tag.get("content", "").strip()
        
        return location if location else None

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract location from JSON-LD structured data"""
        json_scripts = soup.find_all("script", {"type": "application/ld+json"})
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                
                # Handle both single objects and arrays
                items = data if isinstance(data, list) else [data]
                
                for item in items:
                    location = {}
                    
                    # Check for Place or LocalBusiness schema
                    if item.get("@type") in ["Place", "LocalBusiness", "Restaurant", "Hotel", "TouristAttraction"]:
                        # Address
                        if "address" in item:
                            addr = item["address"]
                            if isinstance(addr, dict):
                                address_parts = []
                                if addr.get("streetAddress"):
                                    address_parts.append(addr["streetAddress"])
                                if addr.get("addressLocality"):
                                    address_parts.append(addr["addressLocality"])
                                    location["city"] = addr["addressLocality"]
                                if addr.get("addressRegion"):
                                    location["region"] = addr["addressRegion"]
                                if address_parts:
                                    location["address"] = ", ".join(address_parts)
                            elif isinstance(addr, str):
                                location["address"] = addr
                        
                        # Geo coordinates
                        if "geo" in item and isinstance(item["geo"], dict):
                            geo = item["geo"]
                            if geo.get("latitude") and geo.get("longitude"):
                                try:
                                    location["latitude"] = float(geo["latitude"])
                                    location["longitude"] = float(geo["longitude"])
                                except (ValueError, TypeError):
                                    pass
                        
                        if location:
                            return location
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(f"Error parsing JSON-LD: {e}")
                continue
        
        return None

    def _extract_from_google_maps(self, soup: BeautifulSoup, html: str) -> Optional[Dict[str, Any]]:
        """Extract location from Google Maps embeds"""
        location = {}
        
        # Google Maps iframe
        iframe = soup.find("iframe", {"src": re.compile(r"google\.com/maps")})
        if iframe:
            src = iframe.get("src", "")
            # Extract coordinates from embed URL
            # Format: .../@lat,lng,zoom
            coords_match = re.search(r'@(-?\d+\.?\d*),(-?\d+\.?\d*)', src)
            if coords_match:
                try:
                    location["latitude"] = float(coords_match.group(1))
                    location["longitude"] = float(coords_match.group(2))
                except (ValueError, TypeError):
                    pass
        
        # Google Maps data attributes
        maps_div = soup.find("div", {"data-lat": True, "data-lng": True})
        if maps_div:
            try:
                location["latitude"] = float(maps_div.get("data-lat", ""))
                location["longitude"] = float(maps_div.get("data-lng", ""))
            except (ValueError, TypeError):
                pass
        
        # Extract from HTML directly (for embedded maps)
        if not location.get("latitude"):
            # Look for data-lat/data-lng attributes
            lat_match = re.search(r'data-lat=["\'](-?\d+\.?\d*)["\']', html)
            lng_match = re.search(r'data-lng=["\'](-?\d+\.?\d*)["\']', html)
            if lat_match and lng_match:
                try:
                    location["latitude"] = float(lat_match.group(1))
                    location["longitude"] = float(lng_match.group(2))
                except (ValueError, TypeError):
                    pass
        
        return location if location else None

    def _extract_coordinates_from_text(self, text: str) -> Optional[Dict[str, float]]:
        """Extract latitude/longitude coordinates from text"""
        # Pattern: "10.6407, 122.9689" or "10.6407°N, 122.9689°E" or "lat: 10.6407, lng: 122.9689"
        patterns = [
            r'(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)',  # "10.6407, 122.9689"
            r'latitude[:\s]+(-?\d+\.?\d*).*?longitude[:\s]+(-?\d+\.?\d*)',  # "latitude: 10.6407, longitude: 122.9689"
            r'lat[:\s]+(-?\d+\.?\d*).*?lng[:\s]+(-?\d+\.?\d*)',  # "lat: 10.6407, lng: 122.9689"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    lat = float(match[0])
                    lng = float(match[1])
                    # Validate coordinates (Bacolod area roughly: 10.5-10.8 lat, 122.8-123.0 lng)
                    if 10.0 <= lat <= 11.0 and 122.0 <= lng <= 123.5:
                        return {"latitude": lat, "longitude": lng}
                except (ValueError, IndexError):
                    continue
        
        return None

    def _extract_address_from_text(self, text: str) -> Optional[str]:
        """Extract address from text using patterns"""
        # Common address patterns for Bacolod
        patterns = [
            r'(\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr)),?\s*(?:,?\s*)?(?:Barangay\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*(?:Bacolod\s+City)?,?\s*(?:Negros\s+Occidental)?',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)),?\s*(?:,?\s*)?(?:Barangay\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s*(?:Bacolod\s+City)?',
            r'(?:located\s+at|address[:\s]+|found\s+at)\s*([^,]+(?:,\s*[^,]+){0,3}),?\s*(?:Bacolod\s+City)?,?\s*(?:Negros\s+Occidental)?',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    address = ", ".join([m.strip() for m in match if m.strip()])
                else:
                    address = match.strip()
                
                # Filter out common false positives
                if address and len(address) > 10 and len(address) < 200:
                    # Check if it contains Bacolod-related keywords
                    address_lower = address.lower()
                    if any(keyword in address_lower for keyword in self.bacolod_keywords):
                        return address + ", Bacolod City, Negros Occidental"
                    elif "bacolod" not in address_lower:
                        # Add Bacolod if not present
                        return address + ", Bacolod City, Negros Occidental"
        
        return None

    def _extract_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract location information from plain text"""
        location = {}
        
        # Extract address
        address = self._extract_address_from_text(text)
        if address:
            location["address"] = address
        
        # Extract coordinates
        coords = self._extract_coordinates_from_text(text)
        if coords:
            location.update(coords)
        
        return location if location else None

    def _extract_city_region(self, text: str) -> Optional[Dict[str, str]]:
        """Extract city and region from text"""
        city = None
        region = None
        
        # Check for Bacolod City
        if re.search(r'bacolod\s+city', text, re.IGNORECASE):
            city = "Bacolod City"
        
        # Check for Negros Occidental
        if re.search(r'negros\s+occidental', text, re.IGNORECASE):
            region = "Negros Occidental"
        elif re.search(r'negros', text, re.IGNORECASE):
            region = "Negros Occidental"
        
        # Default to Bacolod if keywords found
        if any(keyword in text.lower() for keyword in self.bacolod_keywords):
            city = city or "Bacolod City"
            region = region or "Negros Occidental"
        
        return {"city": city, "region": region} if city or region else None
