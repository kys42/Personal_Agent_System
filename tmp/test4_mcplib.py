from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="npx",  # Executable
    args=["-y", "@notionhq/notion-mcp-server"],  # Optional command line arguments
    env={
        "OPENAPI_MCP_HEADERS": '{"Authorization": "Bearer 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", "Notion-Version": "2022-06-28"}'
    },  # Optional environment variables
)


# Optional: create a sampling callback
async def handle_sampling_message(
    message: types.CreateMessageRequestParams,
) -> types.CreateMessageResult:
    return types.CreateMessageResult(
        role="assistant",
        content=types.TextContent(
            type="text",
            text="Hello, world! from model",
        ),
        model="gpt-3.5-turbo",
        stopReason="endTurn",
    )


async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=handle_sampling_message
        ) as session:
            # Initialize the connection
            session_init = await session.initialize()
            print(session_init)

            tools = await session.list_tools()
            print(tools)

            result = await session.call_tool("API-get-users")
            print(result)


            # List available prompts
            prompts = await session.list_prompts()

            # Get a prompt
            prompt = await session.get_prompt(
                "example-prompt", arguments={"arg1": "value"}
            )

            # List available resources
            resources = await session.list_resources()

            # List available tools
            tools = await session.list_tools()

            # Read a resource
            content, mime_type = await session.read_resource("file://some/path")

            # Call a tool
            result = await session.call_tool("notion_search", arguments={"query": "test"})


if __name__ == "__main__":
    import asyncio

    asyncio.run(run())