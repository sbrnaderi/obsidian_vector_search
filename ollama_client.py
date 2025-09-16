import httpx
import asyncio
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OllamaEmbeddingClient:
    """Client for generating embeddings using Ollama"""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []

        for text in texts:
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                response.raise_for_status()

                result = response.json()
                if "embedding" in result:
                    embeddings.append(result["embedding"])
                else:
                    logger.error(f"No embedding in response: {result}")
                    embeddings.append([])

            except Exception as e:
                logger.error(f"Error generating embedding for text: {e}")
                embeddings.append([])

        return embeddings

    async def health_check(self) -> bool:
        """Check if Ollama server is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def check_model_exists(self) -> bool:
        """Check if the embedding model exists"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                return self.model in model_names
            return False
        except Exception as e:
            logger.error(f"Error checking model existence: {e}")
            return False