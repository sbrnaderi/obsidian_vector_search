#!/usr/bin/env python3
"""
MCP Server for Obsidian Vector Search
Provides AI models with semantic search capabilities for Obsidian vaults
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from config import get_settings
from ollama_client import OllamaEmbeddingClient
from vector_db import VectorDatabase
from indexer import ObsidianIndexer

# Configure logging to stderr (never stdout for MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Global components
settings = None
ollama_client = None
vector_db = None
indexer = None

async def initialize_components():
    """Initialize all components needed for the MCP server"""
    global settings, ollama_client, vector_db, indexer

    try:
        settings = get_settings()
        logger.info(f"Initialized settings - Vault: {settings.vault_path}")

        # Initialize Ollama client
        ollama_client = OllamaEmbeddingClient(settings.ollama_url, settings.embedding_model)
        logger.info(f"Initialized Ollama client - URL: {settings.ollama_url}")

        # Test Ollama connection
        if not await ollama_client.health_check():
            logger.warning("Ollama server is not accessible")
        else:
            logger.info("Ollama server is accessible")

        # Initialize vector database
        vector_db = VectorDatabase(settings.chroma_persist_directory)
        db_info = vector_db.get_collection_info()
        logger.info(f"Initialized vector database - Documents: {db_info['document_count']}")

        # Initialize indexer
        indexer = ObsidianIndexer(settings.vault_path, vector_db, ollama_client)
        logger.info("Initialized indexer")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return False

# Create MCP server
server = Server("obsidian-vector-search")

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="search_obsidian",
            description="Search your Obsidian vault using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query (e.g., 'machine learning concepts', 'project ideas')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-50)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_document_content",
            description="Get the full content of a specific document from your Obsidian vault",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document (from search results)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="get_vault_statistics",
            description="Get statistics about your Obsidian vault and the vector database",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="reindex_vault",
            description="Manually trigger reindexing of your Obsidian vault",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""

    if name == "search_obsidian":
        return await search_obsidian_tool(arguments)
    elif name == "get_document_content":
        return await get_document_content_tool(arguments)
    elif name == "get_vault_statistics":
        return await get_vault_statistics_tool(arguments)
    elif name == "reindex_vault":
        return await reindex_vault_tool(arguments)
    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

async def search_obsidian_tool(arguments: dict) -> List[TextContent]:
    """Search Obsidian vault using semantic similarity"""
    try:
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)

        logger.info(f"Searching for: '{query}' (limit: {limit})")

        if not ollama_client or not vector_db:
            result = {"error": "Vector search components not initialized"}
            return [TextContent(type="text", text=json.dumps(result))]

        if not query.strip():
            result = {"error": "Query cannot be empty"}
            return [TextContent(type="text", text=json.dumps(result))]

        # Validate limit
        limit = max(1, min(50, limit))

        # Generate embedding for query
        query_embedding = await ollama_client.generate_embedding(query)

        if not query_embedding:
            result = {"error": "Failed to generate embedding for query"}
            return [TextContent(type="text", text=json.dumps(result))]

        # Search vector database
        search_results = vector_db.search(query_embedding, limit)

        # Format results for AI consumption
        formatted_results = []
        for result in search_results.get("results", []):
            metadata = result.get("metadata", {})

            formatted_result = {
                "file_name": metadata.get("file_name", "Unknown"),
                "file_path": metadata.get("file_path", "Unknown"),
                "content": result.get("content", ""),
                "similarity_score": round(1 - result.get("distance", 1), 4),
                "distance": round(result.get("distance", 1), 4),
                "chunk_info": {
                    "chunk_index": metadata.get("chunk_index", 0),
                    "total_chunks": metadata.get("total_chunks", 1),
                    "chunk_size": metadata.get("chunk_size", len(result.get("content", "")))
                },
                "file_info": {
                    "modified_at": metadata.get("modified_at"),
                    "file_size": metadata.get("file_size"),
                    "content_hash": metadata.get("content_hash", "")[:8]  # Short hash for reference
                }
            }
            formatted_results.append(formatted_result)

        response = {
            "query": query,
            "total_results": search_results.get("total_results", 0),
            "results": formatted_results
        }

        logger.info(f"Found {len(formatted_results)} results for query: '{query}'")
        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        error_msg = f"Search failed: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

async def get_document_content_tool(arguments: dict) -> List[TextContent]:
    """Get the full content of a specific document"""
    try:
        file_path = arguments.get("file_path", "")
        logger.info(f"Getting document: {file_path}")

        if not vector_db:
            result = {"error": "Vector database not initialized"}
            return [TextContent(type="text", text=json.dumps(result))]

        # Handle chunked file paths (remove chunk suffix)
        base_file_path = file_path.split('#')[0] if '#' in file_path else file_path

        # Try to get document from database
        document = vector_db.get_document_by_path(base_file_path)

        if document:
            metadata = document.get("metadata", {})
            response = {
                "file_path": base_file_path,
                "file_name": metadata.get("file_name", "Unknown"),
                "content": document.get("content", ""),
                "metadata": {
                    "file_size": metadata.get("file_size"),
                    "modified_at": metadata.get("modified_at"),
                    "created_at": metadata.get("created_at"),
                    "chunk_info": {
                        "chunk_index": metadata.get("chunk_index", 0),
                        "total_chunks": metadata.get("total_chunks", 1)
                    }
                }
            }
            return [TextContent(type="text", text=json.dumps(response, indent=2))]
        else:
            result = {"error": f"Document not found: {file_path}"}
            return [TextContent(type="text", text=json.dumps(result))]

    except Exception as e:
        error_msg = f"Failed to get document: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

async def get_vault_statistics_tool(arguments: dict) -> List[TextContent]:
    """Get statistics about the vault and database"""
    try:
        logger.info("Getting vault statistics")

        if not vector_db or not indexer:
            result = {"error": "Components not initialized"}
            return [TextContent(type="text", text=json.dumps(result))]

        # Get database info
        db_info = vector_db.get_collection_info()

        # Get vault stats
        vault_stats = indexer.get_vault_stats()

        # Get Ollama connection status
        ollama_status = await ollama_client.health_check() if ollama_client else False
        model_exists = await ollama_client.check_model_exists() if ollama_client else False

        response = {
            "vault": {
                "path": vault_stats.get("vault_path"),
                "total_files": vault_stats.get("total_files", 0),
                "total_size_mb": round(vault_stats.get("total_size_bytes", 0) / 1024 / 1024, 2)
            },
            "database": {
                "indexed_documents": db_info.get("document_count", 0),
                "collection_name": db_info.get("collection_name")
            },
            "system": {
                "ollama_connected": ollama_status,
                "embedding_model": settings.embedding_model if settings else "unknown",
                "model_available": model_exists
            }
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        error_msg = f"Failed to get statistics: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg}))]

async def reindex_vault_tool(arguments: dict) -> List[TextContent]:
    """Manually trigger reindexing of the vault"""
    try:
        logger.info("Starting manual vault reindexing")

        if not indexer:
            result = {"error": "Indexer not initialized"}
            return [TextContent(type="text", text=json.dumps(result))]

        # Trigger reindexing
        result = await indexer.index_vault()

        response = {
            "status": "completed",
            "results": {
                "processed": result.get("processed", 0),
                "errors": result.get("errors", 0),
                "skipped": result.get("skipped", 0),
                "total_files": result.get("total_files", 0)
            },
            "message": f"Reindexing completed. Processed {result.get('processed', 0)} files."
        }

        logger.info(f"Reindexing completed: {response['results']}")
        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        error_msg = f"Reindexing failed: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=json.dumps({"error": error_msg, "status": "failed"}))]

async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Obsidian Vector Search MCP Server...")

    # Initialize components
    if not await initialize_components():
        logger.error("Failed to initialize components. Exiting.")
        sys.exit(1)

    logger.info("MCP Server initialized successfully")

    # Run the MCP server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"MCP Server error: {e}")
        sys.exit(1)