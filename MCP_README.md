# Obsidian Vector Search MCP Server

A Model Context Protocol (MCP) server that gives AI models direct access to your Obsidian vault through semantic search capabilities.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
uv pip install -r requirements.txt
```

### 2. Test the MCP Server

```bash
python test_mcp.py
```

### 3. Configure Claude Desktop

#### Option A: Manual Configuration

1. **Find your Claude Desktop config file**:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the MCP server configuration**:
   ```json
   {
     "mcpServers": {
       "obsidian-vector-search": {
         "command": "uv",
         "args": [
           "--directory",
           "/ABSOLUTE/PATH/TO/YOUR/PROJECT",
           "run",
           "mcp_server.py"
         ],
         "env": {
           "PYTHONPATH": "/ABSOLUTE/PATH/TO/YOUR/PROJECT"
         }
       }
     }
   }
   ```

3. **Update the path**: Replace `/ABSOLUTE/PATH/TO/YOUR/PROJECT` with your actual project path

#### Option B: Use Provided Config

Copy the provided configuration:
```bash
# Update the path in claude_desktop_config.json first
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 4. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the MCP server.

## 🔧 Available Tools

The MCP server exposes these tools to AI models:

### `search_obsidian`
**Search your Obsidian vault using semantic similarity**
- **Parameters**:
  - `query` (string): Natural language search query
  - `limit` (integer, optional): Max results (1-50, default: 10)
- **Returns**: JSON with search results, similarity scores, and metadata

### `get_document_content`
**Get full content of a specific document**
- **Parameters**:
  - `file_path` (string): Document path from search results
- **Returns**: JSON with complete document content and metadata

### `get_vault_statistics`
**Get statistics about your vault and database**
- **Returns**: JSON with vault files, database status, and system info

### `reindex_vault`
**Manually trigger vault reindexing**
- **Returns**: JSON with indexing results and statistics

## 💡 Usage Examples

Once configured, AI models can use these tools directly in conversations:

### Search Example
```
AI: I'll search your Obsidian vault for information about machine learning.

[Uses search_obsidian tool with query "machine learning"]

Based on your notes, I found several relevant documents about machine learning concepts...
```

### Document Retrieval Example
```
AI: Let me get the full content of that specific document you mentioned.

[Uses get_document_content tool with file path]

Here's the complete content from your note about neural networks...
```

## 🔍 How It Works

1. **Direct Database Access**: The MCP server connects directly to your Chroma vector database
2. **Semantic Search**: Uses your Ollama embedding model for similarity matching
3. **Real-time Results**: AI models get instant access to your vault content
4. **Contextual Integration**: Search results are seamlessly integrated into AI conversations

## 📋 Prerequisites

- Your Obsidian vector search API must be set up (database and embeddings created)
- Ollama server running with your embedding model
- Claude Desktop or other MCP-compatible AI client

## 🛠️ Troubleshooting

### MCP Server Not Loading
1. Check Claude Desktop config file syntax (must be valid JSON)
2. Verify absolute paths are correct
3. Ensure all dependencies are installed
4. Check Claude Desktop logs for errors

### Search Not Working
1. Run `python test_mcp.py` to test locally
2. Verify your `.env` configuration
3. Check that Ollama server is accessible
4. Ensure vector database has indexed documents

### Performance Issues
1. Limit search results for faster responses
2. Consider reducing chunk size in indexer
3. Monitor Ollama server performance

## 🔐 Security Considerations

- The MCP server gives AI models direct access to your Obsidian vault
- All content in your vault becomes searchable by AI models
- Consider which AI clients you trust with this access
- Monitor usage through logs if needed

## 🎯 Benefits

### For AI Conversations
- **Contextual Responses**: AI can reference your specific notes and knowledge
- **Real-time Search**: No need to manually find and copy relevant content
- **Comprehensive Understanding**: AI can cross-reference multiple documents

### For Knowledge Management
- **Enhanced Discovery**: Find connections between notes you might have missed
- **Dynamic Retrieval**: Get relevant context automatically during conversations
- **Seamless Integration**: Works with any MCP-compatible AI client

## 📊 Monitoring

The MCP server logs all operations to stderr. Monitor logs for:
- Search queries and results
- Database operations
- Connection status
- Error conditions

## 🔄 Updates and Maintenance

- The MCP server uses your existing indexing system
- New documents are automatically available after reindexing
- No additional maintenance required beyond your existing setup

## 🤝 Integration with Other Tools

The MCP server can work alongside:
- Your existing FastAPI search service
- Gradio web interface
- Other MCP servers in Claude Desktop
- Custom MCP clients

This gives you multiple ways to access your Obsidian vault while maintaining a single source of truth.