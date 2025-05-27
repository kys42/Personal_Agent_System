import asyncio
from typing import List, Dict, Any, Optional

from model_wrapper import ModelWrapper, Message # Assuming Message and ModelWrapper are defined in model_wrapper.py
from mcp import client # MCP Client components
from mcp import types as mcp_types # MCP type definitions

class Orchestrator:
    def __init__(self, model_wrapper: ModelWrapper, mcp_server_url: str = "http://localhost:8000/mcp"):
        self.model_wrapper = model_wrapper
        self.mcp_server_url = mcp_server_url
        self.mcp_session: Optional[client.ClientSession] = None
        self._mcp_client_cm = None # To hold the context manager for streamablehttp_client

    async def _connect_mcp(self):
        if self.mcp_session and not self.mcp_session.closed:
            return
        print(f"Orchestrator: Connecting to MCP Server at {self.mcp_server_url}")
        self._mcp_client_cm = client.streamable_http.streamablehttp_client(self.mcp_server_url)
        read_stream, write_stream, _ = await self._mcp_client_cm.__aenter__()
        self.mcp_session = client.ClientSession(read_stream, write_stream)
        await self.mcp_session.initialize()
        print("Orchestrator: Connected to MCP Server and initialized session.")

    async def _disconnect_mcp(self):
        if self.mcp_session:
            await self.mcp_session.close()
            self.mcp_session = None
            print("Orchestrator: MCP session closed.")
        if self._mcp_client_cm:
            await self._mcp_client_cm.__aexit__(None, None, None)
            self._mcp_client_cm = None
            print("Orchestrator: MCP client connection released.")

    async def _get_mcp_tools_formatted_for_model(self) -> List[Dict[str, Any]]:
        if not self.mcp_session:
            await self._connect_mcp()
        
        mcp_tools: List[mcp_types.Tool] = await self.mcp_session.list_tools()
        formatted_tools = []
        for tool in mcp_tools:
            # This transformation assumes OpenAI-like function definition format.
            # The mcp.types.Tool.parameters_json_schema should provide the schema.
            parameters = tool.parameters_json_schema or {"type": "object", "properties": {}}
            formatted_tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "parameters": parameters
            })
        print(f"Orchestrator: Fetched and formatted {len(formatted_tools)} tools from MCP server.")
        return formatted_tools

    async def process_message(self, user_message_content: str) -> str:
        await self._connect_mcp() # Ensure connection
        
        conversation_history: List[Message] = [
            Message(role="user", content=user_message_content)
        ]
        
        available_tools = await self._get_mcp_tools_formatted_for_model()
        
        # First call to the model
        model_response: Message = await self.model_wrapper.generate(
            messages=conversation_history,
            functions=available_tools
        )
        
        conversation_history.append(model_response)
        
        # Loop for function calls (simplified: one call for now)
        if model_response.function_call:
            fc = model_response.function_call
            tool_name = fc.name
            tool_args = fc.arguments
            
            print(f"Orchestrator: Model requested function call: {tool_name} with args {tool_args}")
            
            try:
                tool_result_content = await self.mcp_session.call_tool(tool_name, arguments=tool_args)
                print(f"Orchestrator: Tool {tool_name} executed successfully.")
            except Exception as e:
                print(f"Orchestrator: Error calling tool {tool_name}: {e}")
                tool_result_content = f"Error executing tool {tool_name}: {str(e)}"
            
            conversation_history.append(Message(
                role="function", 
                name=tool_name, 
                content=str(tool_result_content)
            ))
            
            # Second call to the model with the function result
            final_model_response: Message = await self.model_wrapper.generate(
                messages=conversation_history,
                functions=available_tools
            )
            return final_model_response.content or "No content from model after function call."
        
        return model_response.content or "No content from model."

    async def close(self):
        """Clean up resources, like closing the MCP client session."""
        await self._disconnect_mcp()
