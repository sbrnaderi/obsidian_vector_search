import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import logging
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorDatabase:
    """Chroma vector database wrapper for document storage and search"""

    def __init__(self, persist_directory: str):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        self.collection_name = "obsidian_documents"
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Get or create the documents collection"""
        try:
            return self.client.get_collection(name=self.collection_name)
        except ValueError:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Obsidian vault documents"}
            )

    def _generate_document_id(self, file_path: str) -> str:
        """Generate a unique document ID from file path"""
        return hashlib.md5(file_path.encode()).hexdigest()

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add multiple documents to the vector database

        Args:
            documents: List of dicts with keys: file_path, content, metadata, embedding
        """
        if not documents:
            return

        ids = []
        embeddings = []
        metadatas = []
        documents_content = []

        for doc in documents:
            doc_id = self._generate_document_id(doc["file_path"])
            ids.append(doc_id)
            embeddings.append(doc["embedding"])

            metadata = {
                "file_path": doc["file_path"],
                "indexed_at": datetime.now().isoformat(),
                **doc.get("metadata", {})
            }
            metadatas.append(metadata)
            documents_content.append(doc["content"])

        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_content
            )
            logger.info(f"Added {len(documents)} documents to vector database")
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {e}")
            raise

    def search(self, query_embedding: List[float], n_results: int = 10) -> Dict[str, Any]:
        """Search for similar documents

        Args:
            query_embedding: Query vector
            n_results: Number of results to return

        Returns:
            Dictionary with search results
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            # Format results
            formatted_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0.0
                    })

            return {
                "results": formatted_results,
                "total_results": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Error searching vector database: {e}")
            return {"results": [], "total_results": 0}

    def get_document_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get a document by file path"""
        doc_id = self._generate_document_id(file_path)
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )

            if results["ids"]:
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0] if results["documents"] else "",
                    "metadata": results["metadatas"][0] if results["metadatas"] else {}
                }
            return None
        except Exception as e:
            logger.error(f"Error getting document by path {file_path}: {e}")
            return None

    def delete_document(self, file_path: str) -> bool:
        """Delete a document by file path"""
        doc_id = self._generate_document_id(file_path)
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {file_path}: {e}")
            return False

    def get_all_document_paths(self) -> List[str]:
        """Get all indexed document file paths"""
        try:
            results = self.collection.get(include=["metadatas"])
            paths = []
            if results["metadatas"]:
                for metadata in results["metadatas"]:
                    if "file_path" in metadata:
                        paths.append(metadata["file_path"])
            return paths
        except Exception as e:
            logger.error(f"Error getting all document paths: {e}")
            return []

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        try:
            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.collection_name
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"document_count": 0, "collection_name": self.collection_name}