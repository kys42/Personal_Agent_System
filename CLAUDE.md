# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based agent system that implements a flexible architecture separating LLM interaction from tool execution using the Model Context Protocol (MCP). The system enables swapping different LLM backends while maintaining consistent tool usage through a unified interface.

## Architecture

- **Model Wrapper** (`model_wrapper.py`): Abstract base class for different LLM implementations (OpenAI, local models)
- **Orchestrator** (`orchestrator.py`): Core agent logic managing conversation state and function calling flow
- **MCP Server** (`mcp_server.py`): Unified server hosting both local tools and proxied external MCP servers
- **Main Agent** (`main_agent.py`): Example implementation demonstrating system usage

## Development Commands

### Starting the System
```bash
# Start MCP server (required first)
python mcp_server.py

# Run the agent (in separate terminal)
python main_agent.py
```

### Dependencies
```bash
# Install requirements
pip install -r requirements.txt
# or with uv
uv pip install -r requirements.txt
```

## Configuration

- **MCP Configuration**: External tools and servers configured in `mcp_config.json`
- **Server URL**: Default MCP server runs on `http://localhost:8000/mcp`
- **API Keys**: Configure in environment variables or directly in model wrapper initialization

## Key Implementation Details

### Model Wrapper Pattern
All LLM implementations must inherit from `ModelWrapper` and implement the async `generate` method. Current implementations include mock behavior for testing without real API keys.

### MCP Tool Discovery
The system automatically discovers and registers tools from external MCP servers defined in `mcp_config.json`. External servers are launched as subprocess and their tools are proxied through the main MCP server.

### Message Flow
1. User query → Orchestrator
2. Orchestrator fetches available tools from MCP server
3. Model generates response (potentially with function calls)
4. Function calls executed via MCP server
5. Results fed back to model for final response

### Adding New Tools
Add functions with `@mcp_server_app.tool()` decorator in `mcp_server.py`. External MCP servers can be added to `mcp_config.json`.

### Adding New Model Wrappers
Create class inheriting from `ModelWrapper`, implement async `generate` method, and update `main_agent.py` initialization.