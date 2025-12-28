"""Test script to discover Bright Data MCP tools"""

import asyncio
import json
import os
import subprocess
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_mcp_tools():
    """Test MCP server and list available tools"""
    api_token = os.getenv("BRIGHT_DATA_API_KEY", "")
    
    if not api_token:
        print("ERROR: BRIGHT_DATA_API_KEY not set in .env")
        return
    
    print(f"OK: API Token found: {api_token[:10]}...")
    
    # Start MCP process
    env = {**dict(os.environ), "API_TOKEN": api_token, "PRO_MODE": "true"}
    
    print("Starting MCP server...")
    process = subprocess.Popen(
        ["npx", "@brightdata/mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        shell=True
    )
    
    await asyncio.sleep(2)  # Give server time to start
    
    # Initialize
    print("Initializing MCP server...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0.0"}
        }
    }
    
    process.stdin.write(json.dumps(init_request) + "\n")
    process.stdin.flush()
    
    await asyncio.sleep(1)
    
    # Read init response
    init_response = process.stdout.readline()
    print(f"Init response: {init_response.strip()}")
    
    # List tools
    print("Listing available tools...")
    tools_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    process.stdin.write(json.dumps(tools_request) + "\n")
    process.stdin.flush()
    
    await asyncio.sleep(2)
    
    # Read tools response
    tools_response = process.stdout.readline()
    print(f"Tools response: {tools_response.strip()}")
    
    try:
        response_data = json.loads(tools_response.strip())
        if "result" in response_data and "tools" in response_data["result"]:
            tools = response_data["result"]["tools"]
            print(f"\nFound {len(tools)} tools:\n")
            for tool in tools:
                name = tool.get("name", "unknown")
                desc = tool.get("description", "No description")
                print(f"  - {name}")
                print(f"    {desc}\n")
            
            # Find LinkedIn/Twitter/Facebook tools
            linkedin_tools = [t for t in tools if "linkedin" in t.get("name", "").lower()]
            twitter_tools = [t for t in tools if "twitter" in t.get("name", "").lower() or "x" in t.get("name", "").lower()]
            facebook_tools = [t for t in tools if "facebook" in t.get("name", "").lower()]
            
            print("\nSocial Media Tools Found:")
            if linkedin_tools:
                print(f"  LinkedIn: {[t['name'] for t in linkedin_tools]}")
            else:
                print("  LinkedIn: NOT FOUND")
            
            if twitter_tools:
                print(f"  Twitter/X: {[t['name'] for t in twitter_tools]}")
            else:
                print("  Twitter/X: NOT FOUND")
            
            if facebook_tools:
                print(f"  Facebook: {[t['name'] for t in facebook_tools]}")
            else:
                print("  Facebook: NOT FOUND")
        else:
            print(f"ERROR: Unexpected response format: {response_data}")
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        print(f"Raw response: {tools_response}")
    
    process.terminate()
    process.wait()

if __name__ == "__main__":
    print("=" * 60)
    print("Bright Data MCP Tool Discovery Test")
    print("=" * 60)
    asyncio.run(test_mcp_tools())

