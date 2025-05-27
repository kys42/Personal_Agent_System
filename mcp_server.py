from mcp.server.fastmcp import FastMCP

# Create an MCP server instance. 
# Naming it 'mcp_server_app' to avoid confusion with the 'mcp' library import.
mcp_server_app = FastMCP(
    name="MyAgentToolsServer",
    version="0.1.0",
    description="A server exposing tools for the agent architecture."
)

@mcp_server_app.tool()
def notion_read(page_id: str) -> str:
    """Reads content from a (mocked) Notion page."""
    # In a real application, this would interact with the Notion API.
    print(f"[MCP Server] notion_read called with page_id: {page_id}")
    return f"Mock content of Notion page: {page_id}. Lorem ipsum dolor sit amet."

@mcp_server_app.tool()
def fs_read(path: str) -> str:
    """Reads content from a (mocked) local file."""
    # In a real application, this would read from the file system.
    # Ensure proper security and path validation.
    print(f"[MCP Server] fs_read called with path: {path}")
    if path == "/example/file.txt":
        return "Mock content from /example/file.txt: Hello from the file system!"
    return f"Error: File not found at mock path {path}"

# This allows the server to be run directly, e.g., `python mcp_server.py`
# It will use the default transport (likely stdio or a configured default).
if __name__ == "__main__":
    print("Starting MCP Server...")
    # You might need to specify transport, e.g., mcp_server_app.run(transport="stdio")
    # or mcp_server_app.run(transport="streamable-http") depending on client needs.
    # For now, let's assume stdio for simplicity if run directly.
    mcp_server_app.run(transport="streamable-http") # Using streamable-http as it's more common for services
