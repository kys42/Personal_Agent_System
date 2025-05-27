import asyncio
import subprocess
import time
import sys

from orchestrator import Orchestrator
from model_wrapper import OpenAIWrapper # Or LocalLLMWrapper

async def main():
    print("Starting main_agent.py...")
    
    # --- Configuration ---
    # Replace with your actual OpenAI API key if using OpenAIWrapper
    openai_api_key = "YOUR_OPENAI_API_KEY_HERE" 
    mcp_server_url = "http://localhost:8000/mcp" # Default for mcp_server.py
    
    # Choose your model wrapper
    # model = OpenAIWrapper(api_key=openai_api_key)
    # For testing without a real API key, let's use a mock that doesn't need one if available
    # or stick to OpenAIWrapper which has mock logic for now.
    model = OpenAIWrapper(api_key=openai_api_key if openai_api_key != "YOUR_OPENAI_API_KEY_HERE" else "mock_key")
    
    # Initialize the Orchestrator
    agent_orchestrator = Orchestrator(model_wrapper=model, mcp_server_url=mcp_server_url)
    
    print("Orchestrator initialized.")
    print("IMPORTANT: Ensure mcp_server.py is running in a separate terminal.")
    print(f"Attempting to connect to MCP server at {mcp_server_url}\n")
    
    # --- Example Interaction ---
    # Test case 1: A general query (should result in a direct text response)
    user_query1 = "Hello, how are you today?"
    print(f"User: {user_query1}")
    try:
        response1 = await agent_orchestrator.process_message(user_query1)
        print(f"Agent: {response1}")
    except Exception as e:
        print(f"Error processing message 1: {e}")
        print("This might be because the MCP server is not running or not reachable.")
    
    print("\n---\n")
    
    # Test case 2: A query that should trigger the 'notion_read' tool
    user_query2 = "Can you read my notion page about project X?"
    print(f"User: {user_query2}")
    try:
        response2 = await agent_orchestrator.process_message(user_query2)
        print(f"Agent: {response2}")
    except Exception as e:
        print(f"Error processing message 2: {e}")

    # --- Cleanup ---
    print("\nCleaning up orchestrator resources...")
    await agent_orchestrator.close()
    print("Orchestrator closed. main_agent.py finished.")

if __name__ == "__main__":
    # Check if mcp library is installed
    try:
        import mcp
    except ImportError:
        print("MCP library not found. Please install it, e.g., 'pip install mcp' or 'uv add mcp'")
        sys.exit(1)

    # Check if pydantic is installed (dependency for model_wrapper)
    try:
        import pydantic
    except ImportError:
        print("Pydantic library not found. Please install it, e.g., 'pip install pydantic' or 'uv add pydantic'")
        sys.exit(1)

    asyncio.run(main())