from typing import TypedDict, List

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

class MCPToolAdapter:
    def __init__(self, mcp_tool, session):
        self.name = mcp_tool.name
        self.description = mcp_tool.description
        self._schema = mcp_tool.inputSchema
        self._session = session

    async def invoke(self, args: dict) -> dict:
        # call the MCP tool by name, passing the JSON args through
        return await self._session.call_tool(self.name, arguments=args)

class State(TypedDict):
    # messages 키가 리스트 형태로 누적되도록 add_messages 리듀서를 지정
    messages: List[HumanMessage | AIMessage]

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

            # ① list_tools() 전체 응답을 받고
            tools_response = await session.list_tools()

            # ② 실제 Tool 객체 리스트는 response.tools
            mcp_tools = tools_response.tools  
            
            # ③ 각 Tool 객체는 .name, .description, .inputSchema 속성을 가집니다.
            #    이를 어댑터로 래핑
            adapters = [ MCPToolAdapter(t, session) for t in mcp_tools ]
            # 1) 어댑터 리스트(adapters)가 이미 있다면…
            wrapped_tools = []
            for adapter in adapters:
                # adapter.name, adapter.description, adapter.invoke(args) 를 사용
                async def fn(**kwargs):
                    return await adapter.invoke(kwargs)
                # 함수 메타데이터 설정
                fn.__name__ = adapter.name             # 함수 이름이 툴 이름으로 사용됨
                fn.__doc__ = adapter.description       # 도큐먼트 문자열에 설명 저장
                wrapped_tools.append(fn)
            
            # 2) langgraph ToolNode에 등록
            tool_node = ToolNode(tools=wrapped_tools)
            graph = StateGraph(State)
            graph.add_node("tools", tool_node)

            print("test")




if __name__ == "__main__":
    import asyncio

    asyncio.run(run())