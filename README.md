# Obsidian Vector Search API

A FastAPI application that creates a vector database from your Obsidian vault and provides semantic search capabilities using Ollama embeddings and Chroma vector database.

## Features

- 🔍 **Semantic Search**: Search your Obsidian notes using natural language
- 🤖 **Ollama Integration**: Uses mxbai-embed-large embedding model via Ollama
- 📊 **Chroma Vector DB**: Lightweight, persistent vector database
- 🔄 **Auto-Indexing**: Periodic updates to keep your search index current
- 🚀 **Fast API**: RESTful API with automatic documentation
- 📱 **Easy Setup**: Simple configuration and startup

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and update it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
OLLAMA_URL=http://your-ollama-server:11434
EMBEDDING_MODEL=mxbai-embed-large:latest
VAULT_PATH=/path/to/your/obsidian/vault
```

### 3. Start Ollama and Pull Model

Make sure Ollama is running on your server and the embedding model is available:

```bash
ollama pull mxbai-embed-large:latest
```

### 4. Start the API

```bash
python start.py
```

The API will be available at `http://localhost:8000`

### 5. Start the Web UI (Optional)

For a user-friendly web interface, you can also start the Gradio UI:

```bash
python start_ui.py
```

The web UI will be available at `http://localhost:7860`

## API Endpoints

### Search Documents
```bash
POST /search
Content-Type: application/json

{
    "query": "machine learning concepts",
    "limit": 10
}
```

### Manual Reindex
```bash
POST /reindex
```

### Health Check
```bash
GET /health
```

### Get Statistics
```bash
GET /stats
```

### Delete Document
```bash
DELETE /documents/{file_path}
```

## Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `EMBEDDING_MODEL` | `mxbai-embed-large:latest` | Embedding model name |
| `VAULT_PATH` | *required* | Path to Obsidian vault |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | Vector database storage path |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `INDEX_INTERVAL_MINUTES` | `30` | Auto-indexing interval |

## How It Works

1. **File Processing**: Scans your Obsidian vault for `.md` files
2. **Text Chunking**: Splits large documents into overlapping chunks for better search
3. **Embedding Generation**: Uses Ollama to generate embeddings for each chunk
4. **Vector Storage**: Stores embeddings in Chroma database with metadata
5. **Semantic Search**: Converts search queries to embeddings and finds similar documents
6. **Auto-Updates**: Periodically checks for new or modified files

## Development

### Project Structure
```
obsidian_vector_search/
├── main.py              # FastAPI application
├── config.py            # Configuration management
├── ollama_client.py     # Ollama API client
├── vector_db.py         # Chroma database wrapper
├── indexer.py           # File processing and indexing
├── start.py             # Startup script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
└── README.md           # This file
```

### Running in Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Web Interface

The Gradio web UI provides an easy-to-use interface with:

- 🔍 **Search Tab**: Enter queries and view results with similarity scores
- ⚙️ **System Tab**: Check API connection, view statistics, and manually reindex
- 📊 **Real-time Stats**: View vault and database statistics
- 🔄 **Manual Controls**: Force reindexing and connection testing

## API Documentation

Once the server is running, visit:
- **Web UI**: http://localhost:7860 (if started with `start_ui.py`)
- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc

## Troubleshooting

### Common Issues

1. **"Cannot connect to Ollama server"**
   - Verify Ollama is running: `ollama list`
   - Check the `OLLAMA_URL` in your `.env` file
   - Ensure network connectivity to the Ollama server

2. **"Embedding model not found"**
   - Pull the model: `ollama pull mxbai-embed-large:latest`
   - Verify with: `ollama list`

3. **"Vault path does not exist"**
   - Check the `VAULT_PATH` in your `.env` file
   - Ensure the path is accessible and contains `.md` files

4. **Slow indexing**
   - Reduce batch size in indexer
   - Check Ollama server performance
   - Consider using a smaller embedding model for testing

### Logs

The application logs important information to help with debugging:
- Indexing progress and errors
- API request handling
- Database operations
- Ollama connectivity issues

## License

This project is open source and available under the MIT License.