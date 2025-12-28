"""Bright Data MCP Client - Uses official MCP SDK with StdioServerParameters"""

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    # Fallback if MCP SDK not installed
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None

from app.config import settings

logger = logging.getLogger(__name__)


class BrightDataMCPClient:
    """Client for Bright Data MCP server using official MCP SDK"""

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or settings.bright_data_api_key
        self._session: Optional[ClientSession] = None
        self._lock = asyncio.Lock()
        self._available_tools: List[str] = []

    async def _ensure_session(self):
        """Ensure MCP session is initialized"""
        if self._session is not None:
            return

        async with self._lock:
            if self._session is not None:
                return

            if ClientSession is None:
                raise ImportError("MCP SDK not installed. Run: poetry add mcp")

            if not self.api_token:
                raise ValueError("Bright Data API token not configured")

            # Create server parameters with optional Bright Data env vars
            env_vars = {
                "API_TOKEN": self.api_token,
                "PRO_MODE": "true",
            }
            
            # Add optional environment variables if configured
            if settings.bright_data_web_unlocker_zone:
                env_vars["WEB_UNLOCKER_ZONE"] = settings.bright_data_web_unlocker_zone
            if settings.bright_data_browser_auth:
                env_vars["BROWSER_AUTH"] = settings.bright_data_browser_auth
            
            server_params = StdioServerParameters(
                command="npx",
                env=env_vars,
                args=["@brightdata/mcp"],
            )

            # Create stdio client and session
            stdio_transport = await stdio_client(server_params)
            read_stream, write_stream = stdio_transport
            self._session = ClientSession(read_stream, write_stream)
            
            # Initialize the session
            await self._session.__aenter__()
            
            # List available tools
            tools_result = await self._session.list_tools()
            self._available_tools = [tool.name for tool in tools_result.tools]
            logger.info(f"MCP server initialized with {len(self._available_tools)} tools")
            for tool in tools_result.tools:
                logger.info(f"  - {tool.name}: {tool.description[:100]}")

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool"""
        try:
            await self._ensure_session()
            
            result = await self._session.call_tool(tool_name, arguments)
            
            # Parse result content - MCP returns content as list of TextContent objects
            if result.content:
                # Try to parse as JSON if possible
                try:
                    import json
                    text_content = result.content[0].text
                    data = json.loads(text_content)
                    return {"success": True, "data": data}
                except (json.JSONDecodeError, IndexError, AttributeError):
                    # Return as text if not JSON
                    text_content = result.content[0].text if result.content else ""
                    return {"success": True, "data": {"text": text_content}}
            else:
                return {"success": True, "data": {}}
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def search_linkedin(self, name: str, first_name: Optional[str] = None, last_name: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Search LinkedIn for a person by name using web_data_linkedin_people_search"""
        # Use provided first_name/last_name if available, otherwise parse from name
        if first_name and last_name:
            parsed_first = first_name.strip()
            parsed_last = last_name.strip()
        else:
            # Parse name into first and last name
            name_parts = name.strip().split(maxsplit=1)
            parsed_first = name_parts[0] if name_parts else ""
            parsed_last = name_parts[1] if len(name_parts) > 1 else ""
        
        if not parsed_first:
            return {"success": False, "error": "First name is required for LinkedIn search"}
        
        # Use LinkedIn people search tool
        linkedin_search_url = "https://www.linkedin.com/search/results/people/"
        
        logger.info(f"Searching LinkedIn for: {parsed_first} {parsed_last}")
        return await self._call_mcp_tool(
            "web_data_linkedin_people_search",
            {
                "url": linkedin_search_url,
                "first_name": parsed_first,
                "last_name": parsed_last
            }
        )

    async def search_twitter(self, name: str, limit: int = 10) -> Dict[str, Any]:
        """Search Twitter/X for a person by name using search_engine"""
        if not name.strip():
            return {"success": False, "error": "Name is required for Twitter search"}
        
        logger.info(f"Searching Twitter/X for: {name}")
        search_query = f"{name} site:twitter.com OR site:x.com"
        return await self._call_mcp_tool(
            "search_engine",
            {
                "query": search_query,
                "engine": "google"
            }
        )

    async def search_facebook(self, name: str, limit: int = 10) -> Dict[str, Any]:
        """Search Facebook for a person by name using search_engine"""
        if not name.strip():
            return {"success": False, "error": "Name is required for Facebook search"}
        
        logger.info(f"Searching Facebook for: {name}")
        search_query = f"{name} site:facebook.com"
        return await self._call_mcp_tool(
            "search_engine",
            {
                "query": search_query,
                "engine": "google"
            }
        )

    async def close(self):
        """Close the MCP session"""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing MCP session: {e}")
            finally:
                self._session = None


# Global instance
mcp_brightdata_client = BrightDataMCPClient()
