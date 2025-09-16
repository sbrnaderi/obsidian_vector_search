import gradio as gr
import requests
import json
from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ObsidianSearchUI:
    """Gradio UI for Obsidian Vector Search"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip('/')

    def test_api_connection(self) -> tuple[str, str]:
        """Test connection to the API and return status and info"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                status = "🟢 Connected"
                info = f"""
**API Status**: {health_data.get('status', 'unknown')}
**Ollama**: {'✅ Connected' if health_data.get('ollama_connected') else '❌ Disconnected'}
**Database**: {health_data.get('database_status', 'unknown')}
**Vault Path**: {health_data.get('vault_path', 'unknown')}
"""
            else:
                status = "🔴 API Error"
                info = f"HTTP {response.status_code}: {response.text}"
        except requests.exceptions.RequestException as e:
            status = "🔴 Connection Failed"
            info = f"Cannot connect to API at {self.api_url}\nError: {str(e)}"

        return status, info

    def search_documents(self, query: str, limit: int = 10) -> tuple[str, str]:
        """Search documents and return formatted results"""
        if not query.strip():
            return "❌ Error", "Please enter a search query"

        try:
            response = requests.post(
                f"{self.api_url}/search",
                json={"query": query, "limit": limit},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                if not results:
                    return "📭 No Results", f"No documents found for query: '{query}'"

                # Format results
                formatted_results = []
                for i, result in enumerate(results, 1):
                    metadata = result.get('metadata', {})
                    file_name = metadata.get('file_name', 'Unknown')
                    distance = result.get('distance', 0)
                    content_preview = result.get('content', '')[:300] + ('...' if len(result.get('content', '')) > 300 else '')

                    formatted_results.append(f"""
### {i}. {file_name}
**Similarity Score**: {1 - distance:.3f} | **Distance**: {distance:.3f}
**Content**: {content_preview}

---
""")

                status = f"✅ Found {len(results)} results"
                return status, '\n'.join(formatted_results)

            else:
                return "❌ Search Error", f"API Error {response.status_code}: {response.text}"

        except requests.exceptions.RequestException as e:
            return "❌ Connection Error", f"Failed to search: {str(e)}"

    def get_statistics(self) -> str:
        """Get system statistics"""
        try:
            response = requests.get(f"{self.api_url}/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                vault_stats = stats.get('vault', {})
                db_stats = stats.get('database', {})
                settings = stats.get('settings', {})

                return f"""
## 📊 System Statistics

### Vault Information
- **Total Files**: {vault_stats.get('total_files', 0):,}
- **Total Size**: {vault_stats.get('total_size_bytes', 0) / 1024 / 1024:.2f} MB
- **Path**: {vault_stats.get('vault_path', 'unknown')}

### Database Information
- **Indexed Documents**: {db_stats.get('document_count', 0):,}
- **Collection**: {db_stats.get('collection_name', 'unknown')}

### Configuration
- **Ollama URL**: {settings.get('ollama_url', 'unknown')}
- **Embedding Model**: {settings.get('embedding_model', 'unknown')}
- **Index Interval**: {settings.get('index_interval_minutes', 0)} minutes

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            else:
                return f"❌ Error fetching statistics: HTTP {response.status_code}"
        except Exception as e:
            return f"❌ Error: {str(e)}"

    def manual_reindex(self) -> tuple[str, str]:
        """Trigger manual reindexing"""
        try:
            response = requests.post(f"{self.api_url}/reindex", timeout=300)  # 5 minute timeout
            if response.status_code == 200:
                result = response.json()
                status = "✅ Reindex Complete"
                info = f"""
**Processed**: {result.get('processed', 0)} files
**Errors**: {result.get('errors', 0)} files
**Skipped**: {result.get('skipped', 0)} files
**Total**: {result.get('total_files', 0)} files
"""
                return status, info
            else:
                return "❌ Reindex Failed", f"HTTP {response.status_code}: {response.text}"
        except Exception as e:
            return "❌ Error", f"Reindex failed: {str(e)}"

def create_ui(api_url: str = "http://localhost:8000") -> gr.Blocks:
    """Create and configure the Gradio interface"""

    search_ui = ObsidianSearchUI(api_url)

    with gr.Blocks(
        title="Obsidian Vector Search",
        theme=gr.themes.Soft(),
        css="""
        .container { max-width: 1000px; margin: auto; }
        .search-box { font-size: 16px; }
        .result-box { font-family: 'Monaco', monospace; }
        """
    ) as interface:

        gr.Markdown("# 🔍 Obsidian Vector Search")
        gr.Markdown("*Semantic search for your Obsidian vault using AI embeddings*")

        with gr.Tabs():
            # Search Tab
            with gr.Tab("🔍 Search"):
                with gr.Row():
                    with gr.Column(scale=3):
                        search_input = gr.Textbox(
                            placeholder="Enter your search query (e.g., 'machine learning concepts', 'project ideas')",
                            label="Search Query",
                            elem_classes=["search-box"],
                            lines=2
                        )
                    with gr.Column(scale=1):
                        limit_input = gr.Slider(
                            minimum=1,
                            maximum=50,
                            value=10,
                            step=1,
                            label="Max Results"
                        )

                search_btn = gr.Button("🔍 Search", variant="primary", size="lg")

                with gr.Row():
                    search_status = gr.Textbox(label="Status", interactive=False)

                search_results = gr.Markdown(
                    label="Results",
                    elem_classes=["result-box"],
                    value="Enter a search query above and click Search to find relevant documents in your Obsidian vault."
                )

                # Search functionality
                search_btn.click(
                    fn=search_ui.search_documents,
                    inputs=[search_input, limit_input],
                    outputs=[search_status, search_results]
                )

                # Allow Enter key to trigger search
                search_input.submit(
                    fn=search_ui.search_documents,
                    inputs=[search_input, limit_input],
                    outputs=[search_status, search_results]
                )

            # System Tab
            with gr.Tab("⚙️ System"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### API Connection")
                        connection_btn = gr.Button("🔄 Test Connection")
                        connection_status = gr.Textbox(label="Connection Status", interactive=False)
                        connection_info = gr.Markdown()

                        connection_btn.click(
                            fn=search_ui.test_api_connection,
                            outputs=[connection_status, connection_info]
                        )

                    with gr.Column():
                        gr.Markdown("### Reindex Documents")
                        reindex_btn = gr.Button("🔄 Reindex Vault", variant="secondary")
                        reindex_status = gr.Textbox(label="Reindex Status", interactive=False)
                        reindex_info = gr.Markdown()

                        reindex_btn.click(
                            fn=search_ui.manual_reindex,
                            outputs=[reindex_status, reindex_info]
                        )

                gr.Markdown("### Statistics")
                stats_btn = gr.Button("📊 Refresh Statistics")
                stats_display = gr.Markdown()

                stats_btn.click(
                    fn=search_ui.get_statistics,
                    outputs=[stats_display]
                )

                # Load stats on startup
                interface.load(
                    fn=search_ui.get_statistics,
                    outputs=[stats_display]
                )

                # Load connection status on startup
                interface.load(
                    fn=search_ui.test_api_connection,
                    outputs=[connection_status, connection_info]
                )

        gr.Markdown("""
---
### 💡 Tips
- Use natural language queries (e.g., "machine learning algorithms", "project management techniques")
- Results are ranked by semantic similarity using AI embeddings
- The system automatically updates your index every 30 minutes
- Use the System tab to manually reindex after adding new documents
        """)

    return interface

if __name__ == "__main__":
    # Get API URL from environment or use default
    api_url = os.getenv("API_URL", "http://localhost:8000")

    # Create and launch the interface
    interface = create_ui(api_url)
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )