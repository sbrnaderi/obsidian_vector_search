from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    """Application configuration settings"""

    # Ollama Configuration
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    embedding_model: str = Field(default="mxbai-embed-large:latest", description="Embedding model name")

    # Obsidian Vault Configuration
    vault_path: str = Field(..., description="Path to Obsidian vault directory")

    # Database Configuration
    chroma_persist_directory: str = Field(default="./chroma_db", description="Chroma database persistence directory")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")

    # Indexing Configuration
    index_interval_minutes: int = Field(default=30, description="Indexing interval in minutes")

    # ChromaDB Configuration
    anonymized_telemetry: bool = Field(default=False, description="ChromaDB anonymized telemetry")

    class Config:
        env_file = ".env"
        case_sensitive = False

def get_settings() -> Settings:
    """Get application settings"""
    return Settings()