import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Set
import logging
from datetime import datetime
import hashlib

from ollama_client import OllamaEmbeddingClient
from vector_db import VectorDatabase

logger = logging.getLogger(__name__)

class ObsidianIndexer:
    """Indexes Obsidian vault markdown files into vector database"""

    def __init__(self, vault_path: str, vector_db: VectorDatabase, ollama_client: OllamaEmbeddingClient):
        self.vault_path = Path(vault_path)
        self.vector_db = vector_db
        self.ollama_client = ollama_client

        if not self.vault_path.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")

    def _get_file_hash(self, file_path: Path) -> str:
        """Get MD5 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error getting hash for {file_path}: {e}")
            return ""

    def _read_markdown_file(self, file_path: Path) -> Dict[str, Any]:
        """Read and parse a markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            stat = file_path.stat()
            metadata = {
                "file_name": file_path.name,
                "file_size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "content_hash": self._get_file_hash(file_path)
            }

            return {
                "file_path": str(file_path),
                "content": content,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def _get_all_markdown_files(self) -> List[Path]:
        """Get all markdown files in the vault"""
        markdown_files = []
        for root, dirs, files in os.walk(self.vault_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.endswith('.md') and not file.startswith('.'):
                    markdown_files.append(Path(root) / file)

        return markdown_files

    def _chunk_text(self, text: str, max_chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for better embedding"""
        if len(text) <= max_chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chunk_size

            if end < len(text):
                # Try to break at a sentence or paragraph boundary
                last_period = text.rfind('.', start, end)
                last_newline = text.rfind('\n\n', start, end)

                if last_newline > start:
                    end = last_newline
                elif last_period > start:
                    end = last_period + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end - overlap > start else end

        return chunks

    async def _process_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Process a single markdown file into document chunks"""
        file_data = self._read_markdown_file(file_path)
        if not file_data:
            return []

        # Check if file has changed by comparing with existing document
        existing_doc = self.vector_db.get_document_by_path(str(file_path))
        if existing_doc:
            existing_hash = existing_doc.get("metadata", {}).get("content_hash")
            current_hash = file_data["metadata"]["content_hash"]

            if existing_hash == current_hash:
                logger.debug(f"File unchanged, skipping: {file_path}")
                return []

        logger.info(f"Processing file: {file_path}")

        # Split content into chunks
        chunks = self._chunk_text(file_data["content"])
        documents = []

        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding for chunk
                embedding = await self.ollama_client.generate_embedding(chunk)

                if embedding:
                    chunk_metadata = file_data["metadata"].copy()
                    chunk_metadata.update({
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "chunk_size": len(chunk)
                    })

                    documents.append({
                        "file_path": f"{file_data['file_path']}#{i}" if len(chunks) > 1 else file_data["file_path"],
                        "content": chunk,
                        "metadata": chunk_metadata,
                        "embedding": embedding
                    })

            except Exception as e:
                logger.error(f"Error processing chunk {i} from {file_path}: {e}")

        return documents

    async def index_vault(self, batch_size: int = 10) -> Dict[str, Any]:
        """Index all markdown files in the vault"""
        logger.info(f"Starting indexing of vault: {self.vault_path}")

        # Check Ollama connectivity
        if not await self.ollama_client.health_check():
            raise ConnectionError("Cannot connect to Ollama server")

        if not await self.ollama_client.check_model_exists():
            logger.warning(f"Model {self.ollama_client.model} may not exist. Proceeding anyway.")

        markdown_files = self._get_all_markdown_files()
        logger.info(f"Found {len(markdown_files)} markdown files")

        if not markdown_files:
            return {"processed": 0, "errors": 0, "skipped": 0}

        processed = 0
        errors = 0
        skipped = 0

        # Process files in batches
        for i in range(0, len(markdown_files), batch_size):
            batch = markdown_files[i:i + batch_size]
            batch_documents = []

            for file_path in batch:
                try:
                    file_documents = await self._process_file(file_path)
                    if file_documents:
                        batch_documents.extend(file_documents)
                        processed += 1
                    else:
                        skipped += 1

                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
                    errors += 1

            # Add batch to vector database
            if batch_documents:
                try:
                    self.vector_db.add_documents(batch_documents)
                except Exception as e:
                    logger.error(f"Error adding batch to vector database: {e}")
                    errors += len(batch_documents)

        result = {
            "processed": processed,
            "errors": errors,
            "skipped": skipped,
            "total_files": len(markdown_files)
        }

        logger.info(f"Indexing completed: {result}")
        return result

    async def update_index(self) -> Dict[str, Any]:
        """Update index with new or changed files"""
        return await self.index_vault()

    def get_vault_stats(self) -> Dict[str, Any]:
        """Get statistics about the vault"""
        markdown_files = self._get_all_markdown_files()
        total_size = sum(f.stat().st_size for f in markdown_files if f.exists())

        return {
            "total_files": len(markdown_files),
            "total_size_bytes": total_size,
            "vault_path": str(self.vault_path)
        }