#!/usr/bin/env python3
"""
Startup script for Obsidian Vector Search API
"""
import sys
import os
import asyncio
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings

def check_requirements():
    """Check if all requirements are met"""
    try:
        settings = get_settings()
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure to create a .env file with required settings")
        print("📋 Copy .env.example to .env and update the values")
        return False

    # Check vault path
    if not Path(settings.vault_path).exists():
        print(f"❌ Vault path does not exist: {settings.vault_path}")
        print("💡 Update VAULT_PATH in your .env file")
        return False

    print(f"✅ Vault path: {settings.vault_path}")
    print(f"✅ Ollama URL: {settings.ollama_url}")
    print(f"✅ Embedding model: {settings.embedding_model}")
    print(f"✅ API will run on: http://{settings.api_host}:{settings.api_port}")

    return True

async def test_ollama_connection():
    """Test connection to Ollama"""
    from ollama_client import OllamaEmbeddingClient

    settings = get_settings()
    client = OllamaEmbeddingClient(settings.ollama_url, settings.embedding_model)

    try:
        health = await client.health_check()
        if health:
            print("✅ Ollama server is accessible")

            model_exists = await client.check_model_exists()
            if model_exists:
                print(f"✅ Embedding model '{settings.embedding_model}' is available")
            else:
                print(f"⚠️  Embedding model '{settings.embedding_model}' not found")
                print(f"💡 Run: ollama pull {settings.embedding_model}")
                return False
        else:
            print("❌ Cannot connect to Ollama server")
            print("💡 Make sure Ollama is running and accessible")
            return False

    except Exception as e:
        print(f"❌ Ollama connection error: {e}")
        return False
    finally:
        await client.close()

    return True

def main():
    """Main startup function"""
    print("🚀 Starting Obsidian Vector Search API...")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Test Ollama connection
    print("\n🔍 Testing Ollama connection...")
    if not asyncio.run(test_ollama_connection()):
        sys.exit(1)

    print("\n✅ All checks passed! Starting the API server...")
    print("=" * 50)

    # Start the API server
    import uvicorn
    from main import app

    settings = get_settings()

    try:
        uvicorn.run(
            app,
            host=settings.api_host,
            port=settings.api_port,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()