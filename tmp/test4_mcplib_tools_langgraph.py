import asyncio
from typing import TypedDict, List, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from langchain_core.messages import AIMessage, ToolMessage

# 1) MCPToolAdapter: mcp Tool → invoke(args) 인터페이스로 래핑
class MCPToolAdapter:
    def __init__(self, mcp_tool, session: ClientSession):
        self.name = mcp_tool.name
        self.description = mcp_tool.description
        self._session = session

    async def invoke(self, args: Dict) -> Dict:
        # 실제 MCP 서버에 call_tool 호출
        return await self._session.call_tool(self.name, arguments=args)

# 2) State 스키마: messages에 AIMessage 또는 ToolMessage
class State(TypedDict):
    messages: List[AIMessage | ToolMessage]

async def main():
    # 3) MCP 서버 STDIO 파라미터
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@notionhq/notion-mcp-server", "--transport", "stdio"],
        env={"OPENAPI_MCP_HEADERS": '{"Authorization":"Bearer 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","Notion-Version":"2022-06-28"}'}
    )

    # 4) MCP 세션 연결
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 5) 툴 리스트 가져오기
            resp = await session.list_tools()
            mcp_tools = resp.tools

            # 6) 어댑터 래핑
            adapters = [MCPToolAdapter(t, session) for t in mcp_tools]
            wrapped_tools = []
            for adapter in adapters:
                # adapter.name, adapter.description, adapter.invoke(args) 를 사용
                async def fn(**kwargs):
                    return await adapter.invoke(kwargs)
                # 함수 메타데이터 설정
                fn.__name__ = adapter.name             # 함수 이름이 툴 이름으로 사용됨
                fn.__doc__ = adapter.description       # 도큐먼트 문자열에 설명 저장
                wrapped_tools.append(fn)
            # 7) ToolNode 생성
            tool_node = ToolNode(tools=wrapped_tools)

           # 9) StateGraph 구성, entry point=tools
            graph_builder = StateGraph(State)
            graph_builder.add_node("tools", tool_node)
            graph_builder.set_entry_point("tools")
            compiled = graph_builder.compile()

            # 10) 가짜 AIMessage 생성 (tool_calls 포함)
            test_tool_name = wrapped_tools[0].__name__
            fake_ai = AIMessage(content="", role="assistant")
            fake_ai.tool_calls = [
                {
                    "id": "1",               # 반드시 id 필드를 추가
                    "name": test_tool_name,
                    "args": {}               # 호출 인자
                }
            ]
            # 11) 초기 상태
            init_state: State = {"messages": [fake_ai]}

            # 12) 그래프 실행
            result_state = await compiled.ainvoke(init_state)

            # 13) 결과 출력
            print("=== ToolNode 실행 결과 ===")
            for msg in result_state["messages"]:
                print(f"{msg.name} → {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
