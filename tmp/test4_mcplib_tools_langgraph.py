import asyncio
from typing import TypedDict, List, Dict

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage

# 1) MCPToolAdapter: mcp Tool → invoke(args) 인터페이스로 래핑
class MCPToolAdapter:
    def __init__(self, mcp_tool, session: ClientSession):
        self.name = mcp_tool.name
        self.description = mcp_tool.description
        self._session = session

    async def invoke(self, args: Dict) -> Dict:
        # 실제 MCP 서버에 call_tool 호출
        return await self._session.call_tool(self.name, arguments=args)

# 2) 그래프 상태 스키마 정의
class State(TypedDict):
    # messages: ToolMessage를 포함할 수 있도록 List 타입
    messages: List[ToolMessage]

async def main():
    # 3) MCP 서버 STDIO 파라미터
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@notionhq/notion-mcp-server", "--transport", "stdio"],
        env={"OPENAPI_MCP_HEADERS": '{"Authorization":"Bearer YOUR_TOKEN","Notion-Version":"2022-06-28"}'}
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

            # 8) StateGraph 만들고, entry point를 "tools"로만 설정
            graph_builder = StateGraph(State)
            graph_builder.add_node("tools", tool_node)
            graph_builder.set_entry_point("tools")
            graph = graph_builder.compile()

            # 9) 가짜 ToolCall 메시지 생성
            class FakeCallMsg:
                def __init__(self, tool_name):
                    self.tool_calls = [{"name": tool_name, "arguments": {}}]

            # 가장 첫 번째 툴을 테스트로 골라서
            test_tool = adapters[0].name  
            fake_msg = FakeCallMsg(test_tool)

            # 11) 초기 상태에 fake_msg만 넣는다
            init_state: State = {"messages": [fake_msg]}

            # 12) 그래프 실행 — 함수 호출 대신 invoke 또는 ainvoke 사용
            # 비동기 함수 내에서 await로 비동기 실행:
            result_state = await graph.ainvoke(init_state)

            # 12) 결과 출력: ToolMessage 리스트
            print("=== ToolNode 실행 결과 ===")
            for msg in result_state["messages"]:
                print(f"{msg.name} → {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
