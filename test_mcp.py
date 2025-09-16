#!/usr/bin/env python3
"""
Test script for the Obsidian Vector Search MCP Server
Run this to verify that the MCP server is working correctly
"""

import asyncio
import sys
import json
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import server, initialize_components, search_obsidian_tool, get_vault_statistics_tool

async def test_mcp_server():
    """Test the MCP server functionality"""
    print("🧪 Testing Obsidian Vector Search MCP Server")
    print("=" * 50)

    # Initialize components
    print("1. Initializing components...")
    if not await initialize_components():
        print("❌ Failed to initialize components")
        return False

    print("✅ Components initialized successfully")

    # Test search functionality
    print("\n2. Testing search functionality...")
    try:
        search_result = await search_obsidian_tool({
            "query": "test search query",
            "limit": 3
        })

        if search_result and len(search_result) > 0:
            result_data = json.loads(search_result[0].text)
            if "error" in result_data:
                print(f"⚠️  Search returned error: {result_data['error']}")
            else:
                print(f"✅ Search successful - Found {result_data.get('total_results', 0)} results")
        else:
            print("❌ No search results returned")

    except Exception as e:
        print(f"❌ Search test failed: {e}")

    # Test statistics
    print("\n3. Testing statistics...")
    try:
        stats_result = await get_vault_statistics_tool({})

        if stats_result and len(stats_result) > 0:
            stats_data = json.loads(stats_result[0].text)

            if "error" in stats_data:
                print(f"⚠️  Statistics returned error: {stats_data['error']}")
            else:
                vault_info = stats_data.get("vault", {})
                db_info = stats_data.get("database", {})
                print(f"✅ Statistics successful:")
                print(f"   📁 Vault files: {vault_info.get('total_files', 0)}")
                print(f"   🗃️  Indexed documents: {db_info.get('indexed_documents', 0)}")
        else:
            print("❌ No statistics returned")

    except Exception as e:
        print(f"❌ Statistics test failed: {e}")

    print("\n4. Testing available tools...")
    try:
        # Get the list_tools handler and call it directly
        list_tools_handler = server._request_handlers.get('tools/list')
        if list_tools_handler:
            tools = await list_tools_handler()
            print(f"✅ Available tools: {len(tools)}")
            for tool in tools:
                print(f"   🔧 {tool.name}: {tool.description}")
        else:
            print("⚠️  Could not find tools list handler")

    except Exception as e:
        print(f"❌ Tools listing failed: {e}")

    print("\n" + "=" * 50)
    print("🎉 MCP Server test completed!")
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)