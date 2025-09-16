from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import asyncio
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import get_settings
from ollama_client import OllamaEmbeddingClient
from vector_db import VectorDatabase
from indexer import ObsidianIndexer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
settings = get_settings()
scheduler = AsyncIOScheduler()
ollama_client: Optional[OllamaEmbeddingClient] = None
vector_db: Optional[VectorDatabase] = None
indexer: Optional[ObsidianIndexer] = None

# Pydantic models
class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10

class SearchResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]
    distance: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query: str

class IndexStats(BaseModel):
    processed: int
    errors: int
    skipped: int
    total_files: int

class HealthResponse(BaseModel):
    status: str
    ollama_connected: bool
    database_status: str
    vault_path: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ollama_client, vector_db, indexer

    logger.info("Starting up Obsidian Vector Search API...")

    # Initialize components
    ollama_client = OllamaEmbeddingClient(settings.ollama_url, settings.embedding_model)
    vector_db = VectorDatabase(settings.chroma_persist_directory)
    indexer = ObsidianIndexer(settings.vault_path, vector_db, ollama_client)

    # Start background scheduler
    scheduler.add_job(
        periodic_index_update,
        trigger=IntervalTrigger(minutes=settings.index_interval_minutes),
        id="periodic_index_update",
        replace_existing=True
    )
    scheduler.start()

    logger.info("Application started successfully")

    yield

    # Cleanup
    logger.info("Shutting down...")
    scheduler.shutdown()
    if ollama_client:
        await ollama_client.close()

app = FastAPI(
    title="Obsidian Vector Search API",
    description="Semantic search for Obsidian vault using Ollama embeddings and Chroma vector database",
    version="1.0.0",
    lifespan=lifespan
)

async def periodic_index_update():
    """Background task to periodically update the index"""
    try:
        logger.info("Starting periodic index update...")
        result = await indexer.update_index()
        logger.info(f"Periodic index update completed: {result}")
    except Exception as e:
        logger.error(f"Error in periodic index update: {e}")

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {"message": "Obsidian Vector Search API", "version": "1.0.0"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    ollama_connected = await ollama_client.health_check()
    db_info = vector_db.get_collection_info()

    return HealthResponse(
        status="healthy" if ollama_connected else "degraded",
        ollama_connected=ollama_connected,
        database_status=f"{db_info['document_count']} documents",
        vault_path=settings.vault_path
    )

@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search for documents using semantic similarity"""
    try:
        # Generate embedding for query
        query_embedding = await ollama_client.generate_embedding(request.query)

        if not query_embedding:
            raise HTTPException(status_code=500, detail="Failed to generate embedding for query")

        # Search vector database
        search_results = vector_db.search(query_embedding, request.limit)

        # Format response
        results = [
            SearchResult(
                id=result["id"],
                content=result["content"],
                metadata=result["metadata"],
                distance=result["distance"]
            )
            for result in search_results["results"]
        ]

        return SearchResponse(
            results=results,
            total_results=search_results["total_results"],
            query=request.query
        )

    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/reindex", response_model=IndexStats)
async def manual_reindex(background_tasks: BackgroundTasks):
    """Manually trigger a full reindex"""
    try:
        result = await indexer.index_vault()
        return IndexStats(**result)
    except Exception as e:
        logger.error(f"Reindex error: {e}")
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get statistics about the vault and database"""
    try:
        vault_stats = indexer.get_vault_stats()
        db_info = vector_db.get_collection_info()

        return {
            "vault": vault_stats,
            "database": db_info,
            "settings": {
                "ollama_url": settings.ollama_url,
                "embedding_model": settings.embedding_model,
                "index_interval_minutes": settings.index_interval_minutes
            }
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.delete("/documents/{file_path:path}")
async def delete_document(file_path: str):
    """Delete a document from the index"""
    try:
        success = vector_db.delete_document(file_path)
        if success:
            return {"message": f"Document deleted: {file_path}"}
        else:
            raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )