import json
import os
import time
import subprocess
import requests
import functools
import asyncio
from dotenv import load_dotenv
from fastmcp import Client               # fastmcp.Client 로 외부 서버 list_tools() 호출
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List

# .env 파일에서 필요한 환경 변수(API 키 등) 불러오기
load_dotenv()

# JSON 설정 파일 경로
CONFIG_FILE = "mcp_config.json"

def load_mcp_config(path: str = CONFIG_FILE) -> Dict[str, Any]:
    """Loads the MCP configuration from a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] Config 로드 실패: {e}")
        return {}

def ensure_mcp_args(cfg: Dict[str, Any]) -> None:
    """
    cfg['args']에 --transport sse, --host 0.0.0.0, --port <port> 옵션이
    없는 경우 자동으로 추가합니다. 포트 필드는 cfg['port'] 에서 가져오며,
    없으면 기본 5005로 설정합니다.
    """
    args = cfg.get("args", [])
    # 사용자가 --port 를 직접 적었는지 확인
    has_port_flag = any(arg == "--port" for arg in args)
    # 사용자가 --transport 를 직접 적었는지 확인
    has_transport_flag = any(arg == "--transport" for arg in args)
    # 사용자가 --host 를 직접 적었는지 확인
    has_host_flag = any(arg == "--host" for arg in args)

    # cfg['port'] 가 있으면 그 값을, 없으면 기본 5005
    port_str = str(cfg.get("port", 5005))

    # --transport 옵션이 없으면 추가
    if not has_transport_flag:
        args += ["--transport", "sse"]
    # --host 옵션이 없으면 추가
    if not has_host_flag:
        args += ["--host", "0.0.0.0"]
    # --port 옵션이 없으면, cfg['port'] 값을 사용해 추가
    if not has_port_flag:
        args += ["--port", port_str]

    # 변경된 args와 port 값을 다시 cfg에 저장
    cfg["args"] = args
    cfg["port"] = int(port_str)

def launch_mcp_process(server_key: str, cfg: Dict[str, Any]) -> subprocess.Popen:
    """
    server_key: 'notionApi' 등 JSON에 정의된 키
    cfg 예시 (ensure_mcp_args 후):
      {
        "command": "npx",
        "args": [
          "-y", "@notionhq/notion-mcp-server",
          "--transport", "sse",
          "--host", "0.0.0.0",
          "--port", "5005"
        ],
        "env": { "OPENAPI_MCP_HEADERS": "..." },
        "port": 5005
      }
    """
    # 1) args 내부에 필수 옵션이 없으면 자동으로 붙여 준다
    ensure_mcp_args(cfg)

    # 2) 실제 subprocess 실행
    cmd = [cfg["command"]] + cfg.get("args", [])
    env = os.environ.copy()
    env.update(cfg.get("env", {}))

    print(f"[Launcher] '{server_key}' 실행: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # MCP 서버가 완전히 기동될 시간을 잠시 대기 (약 3초 권장)
    time.sleep(3)
    return proc

def create_proxy_fn(tool_name: str, base_url: str, timeout_s: float):
    """
    tool_name: MCP 클라이언트가 호출할 도구 이름 (예: 'notionRead')
    base_url : 'http://localhost:5005' (Notion MCP가 바인딩된 URL)
    timeout_s: 요청 타임아웃(초)
    """
    @functools.wraps(lambda **kwargs: None)
    def proxy_fn(**kwargs) -> Dict[str, Any]:
        payload = {"tool": tool_name, "args": kwargs}
        try:
            resp = requests.post(base_url, json=payload, timeout=timeout_s)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    proxy_fn.__name__ = tool_name.replace(":", "_").replace("-", "_")
    proxy_fn.__doc__ = f"Proxy for {tool_name} @ {base_url}"
    return proxy_fn

# FastMCP 서버 인스턴스 생성
mcp_server_app = FastMCP(
    name="MyAgentUnifiedServer",
    version="0.2.0",
    description="Local + dynamically discovered external tools"
)

# --- Local Tools 정의(원한다면 추가) ---
@mcp_server_app.tool()
def fs_read(path: str) -> str:
    """Reads content from a (mocked) local file."""
    print(f"[Local MCP] fs_read called with path: {path}")
    if path == "/example/file.txt":
        return "Mock content from /example/file.txt: Hello from the file system!"
    return f"Error: File not found at {path}"

async def discover_external_tools(config: Dict[str, Any], registered_tools: List[str]):
    """
    1) JSON의 mcpServers를 순회하며 각 외부 MCP 서버 프로세스 실행 → base_url 저장
    2) base_url에 fastmcp.Client로 연결하여 list_tools() 호출 → 툴 목록 획득
    3) 모든 툴을 register_tool_schema()로 FastMCP에 등록
    4) registered_tools 리스트에 최종적으로 등록된 툴 이름 추가
    """
    mcp_servers_cfg = config.get("mcpServers", {})
    server_processes: Dict[str, subprocess.Popen] = {}
    base_urls: Dict[str, str] = {}

    # 1) 모든 외부 MCP 서버 프로세스 실행
    for server_key, srv_cfg in mcp_servers_cfg.items():
        proc = launch_mcp_process(server_key, srv_cfg)
        server_processes[server_key] = proc
        port = srv_cfg.get("port", 5005)
        base_urls[server_key] = f"http://localhost:{port}"
        print(f"[Launcher] External MCP server '{server_key}' is running at {base_urls[server_key]}")

    # 2) 각 서버에 fastmcp.Client로 연결해 list_tools() 호출
    for server_key, base_url in base_urls.items():
        client = Client(base_url)
        async with client:
            tools = await client.list_tools()  # HTTP POST /tools/list → 툴 목록 반환
            tool_names = [t.name for t in tools]
            print(f"[Discovery] Server '{server_key}' 제공 툴: {tool_names}")

            # 3) 메타데이터 기반으로 FastMCP에 자동 등록
            for tool in tools:
                proxy_fn = create_proxy_fn(tool.name, base_url, timeout_s=5)
                mcp_server_app.register_tool_schema(
                    name=tool.name,
                    json_schema=tool.params,
                    description=tool.description,
                    handler=proxy_fn
                )
                registered_tools.append(tool.name)
                print(f"[Register External] '{tool.name}' registered from server '{server_key}'")

    return server_processes

if __name__ == "__main__":
    print("Starting Unified MCP Server...")

    # 1) JSON 설정 파일 로드
    config_data = load_mcp_config()

    # 2) 외부 툴 등록 시 도구 이름을 담아둘 리스트
    registered_tools: List[str] = []

    # 3) 비동기로 “외부 툴 디스커버리 + 프로세스 실행” 수행
    try:
        server_procs = asyncio.run(discover_external_tools(config_data, registered_tools))
    except Exception as e:
        print(f"[Error] 외부 툴 디스커버리 중 에러 발생: {e}")
        server_procs = {}

    # 4) 로컬 툴 이름도 registered_tools에 추가
    registered_tools.append("fs_read")

    # 5) 최종 등록된 모든 툴 목록 출력
    print("\n=== FastMCP Server에 최종 등록된 툴 목록 ===")
    for tname in registered_tools:
        print(f"- {tname}")
    print("===========================================\n")

    # 6) FastMCP 서버 실행 (이때 이미 asyncio.run은 종료된 상태이므로 충돌 없음)
    print("Running FastMCP (transport=streamable-http)...")
    try:
        mcp_server_app.run(transport="streamable-http")
    finally:
        # 7) 서버 종료 시 백그라운드 외부 MCP 프로세스 모두 종료
        for key, proc in server_procs.items():
            print(f"[Terminate] stopping external MCP server '{key}'")
            proc.terminate()
            proc.wait()
        print("All external MCP processes terminated.")
