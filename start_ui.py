#!/usr/bin/env python3
"""
Startup script for Obsidian Vector Search Gradio UI
"""
import sys
import os
import requests
import time
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_settings

def check_api_connection(api_url: str, max_retries: int = 5) -> bool:
    """Check if the API is running and accessible"""
    print(f"🔍 Checking API connection at {api_url}...")

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{api_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API is accessible")
                print(f"   Status: {health_data.get('status', 'unknown')}")
                print(f"   Ollama: {'✅ Connected' if health_data.get('ollama_connected') else '❌ Disconnected'}")
                print(f"   Database: {health_data.get('database_status', 'unknown')}")
                return True
            else:
                print(f"⚠️  API returned status {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"⚠️  Attempt {attempt + 1}/{max_retries} failed: {e}")

        if attempt < max_retries - 1:
            print("   Retrying in 2 seconds...")
            time.sleep(2)

    return False

def main():
    """Main startup function"""
    print("🎨 Starting Obsidian Vector Search UI...")
    print("=" * 50)

    # Get settings
    try:
        settings = get_settings()
        api_url = f"http://{settings.api_host}:{settings.api_port}"
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Make sure your .env file is properly configured")
        api_url = "http://localhost:8000"
        print(f"   Using default API URL: {api_url}")

    # Check API connection
    if not check_api_connection(api_url):
        print(f"\n❌ Cannot connect to the API at {api_url}")
        print("\n💡 Make sure the API server is running:")
        print(f"   python start.py")
        print("\n🚀 You can still start the UI, but it won't work until the API is available")

        # Ask user if they want to continue
        try:
            response = input("\nDo you want to start the UI anyway? (y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("👋 Goodbye!")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(1)

    print(f"\n✅ Starting Gradio UI...")
    print(f"   API URL: {api_url}")
    print(f"   UI will be available at: http://localhost:7860")
    print("=" * 50)

    # Set API URL as environment variable for the UI
    os.environ["API_URL"] = api_url

    # Import and start the UI
    try:
        from gradio_ui import create_ui

        interface = create_ui(api_url)
        interface.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True
        )

    except KeyboardInterrupt:
        print("\n👋 UI stopped by user")
    except Exception as e:
        print(f"❌ UI error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()