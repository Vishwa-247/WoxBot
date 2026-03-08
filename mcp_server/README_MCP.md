# WoxBot MCP Server

Exposes WoxBot's RAG pipeline as MCP tools for Claude Desktop integration.

## Tools

| Tool                 | Input                | Output                             |
| -------------------- | -------------------- | ---------------------------------- |
| `search_woxsen_docs` | `query: str`         | Grounded answer + source citations |
| `ingest_pdf`         | `file_path: str`     | Chunks indexed count               |
| `list_documents`     | —                    | List of indexed filenames          |
| `calculate_cgpa`     | `marks: list[float]` | CGPA calculation                   |

## Setup

1. Install FastMCP:

   ```bash
   pip install fastmcp
   ```

2. Run the server:

   ```bash
   cd mcp_server
   python mcp_server.py
   ```

3. Connect from Claude Desktop — add to your MCP config:
   ```json
   {
     "mcpServers": {
       "woxbot": {
         "command": "python",
         "args": ["mcp_server/mcp_server.py"],
         "cwd": "path/to/WoxBot"
       }
     }
   }
   ```

## Security

- Rate limited: 20 requests/minute per client
- All tool calls are audit-logged with timestamp
- File paths validated before ingestion
