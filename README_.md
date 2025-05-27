# Agent Architecture with MCP

This project implements a flexible agent architecture that separates LLM interaction from tool execution using the Model Context Protocol (MCP). The system allows swapping different LLM backends while maintaining consistent tool usage.

## Architecture Overview

```
+----------------+     +------------------+     +------------------+
|   Input        |     |   Agent Core     |     |   Model Wrapper  |
| (e.g., User)   | --> |  (Orchestrator)  | --> |  (e.g., OpenAI,   |
+----------------+     +------------------+     |   Local LLM)     |
                                 |           +------------------+
                                 |                      |
                                 | Function Definitions|
                                 |-------------------->|
                                 |                      |
                                 |                      |
                                 v                      |
                          +----------------+           |
                          |   MCP Client   |<----------+
                          +----------------+
                                 |
                                 | Tool Execution
                                 v
                          +----------------+
                          |   MCP Server   |
                          |  (Tool Host)   |
                          +----------------+
```

## Components

1. **Model Wrapper** (`model_wrapper.py`)
   - Abstract base class `ModelWrapper` with async `generate` method
   - Example implementations: `OpenAIWrapper`, `LocalLLMWrapper`
   - Handles LLM-specific API calls and response formatting

2. **MCP Server** (`mcp_server.py`)
   - Hosts tools using `FastMCP` from the `mcp` library
   - Exposes tools like `notion_read` and `fs_read`
   - Runs as a separate HTTP service (default: http://localhost:8000/mcp)

3. **Orchestrator** (`orchestrator.py`)
   - Core agent logic
   - Manages conversation state
   - Handles function calling flow
   - Connects to MCP server for tool execution

4. **Main Agent** (`main_agent.py`)
   - Example implementation
   - Initializes components and handles user interaction

## Getting Started

### Prerequisites

- Python 3.8+
- `pip` or `uv` for package management

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   or using `uv`:
   ```bash
   uv pip install -r requirements.txt
   ```

### Running the System

1. **Start the MCP Server** (in a separate terminal):
   ```bash
   python mcp_server.py
   ```
   The server will start on http://localhost:8000/mcp by default.

2. **Run the Agent** (in another terminal):
   ```bash
   python main_agent.py
   ```

## Example Usage

The `main_agent.py` includes example interactions that demonstrate:

1. Direct LLM responses to general queries
2. Tool invocation based on user input

Example output:
```
User: Can you read my notion page about project X?
[Orchestrator] Fetching tools from MCP server...
[Model Wrapper] Decided to call notion_read
[Orchestrator] Executing tool: notion_read with args: {'page_id': 'project_x'}
[MCP Server] notion_read called with page_id: project_x
[Orchestrator] Tool execution completed
[Model Wrapper] Processed tool result
Agent: Here's the content from your Notion page about project X...
```

## Adding New Tools

1. Add a new function in `mcp_server.py` with the `@mcp_server_app.tool()` decorator:
   ```python
   @mcp_server_app.tool()
   def my_tool(param1: str, param2: int) -> str:
       """Tool description for the LLM."""
       # Implementation here
       return "Result"
   ```

2. The tool will be automatically discovered and made available to the agent.

## Adding New Model Wrappers

1. Create a new class that inherits from `ModelWrapper`
2. Implement the async `generate` method
3. Update `main_agent.py` to use your new wrapper

## Configuration

- MCP Server URL: Configured in `main_agent.py` (default: http://localhost:8000/mcp)
- Model-specific settings: Configured when initializing the model wrapper

## Dependencies

- `mcp[cli]`: MCP library with CLI tools
- `pydantic`: Data validation
- `uvicorn`: ASGI server (for MCP HTTP transport)
- `fastapi`: Web framework (for MCP HTTP transport)

## Troubleshooting

- **MCP Server not starting**: Ensure ports 8000 is available
- **Connection errors**: Verify the MCP server URL in `main_agent.py` matches the actual server address
- **Missing dependencies**: Run `pip install -r requirements.txt`

## License

[Your License Here]

## Contributing

[Your contribution guidelines here]
