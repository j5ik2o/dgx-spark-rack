"""FreeCAD MCPのstdioクライアント。MCP SDKのあるPythonで実行する。"""

import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True, help="freecad-mcp実行ファイルの絶対パス")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("script", nargs="?", type=Path)
    args = parser.parse_args()
    environment = {key: os.environ[key] for key in
                   ("HOME", "USER", "LOGNAME", "TMPDIR", "PATH", "LANG", "LC_ALL")
                   if key in os.environ}
    parameters = StdioServerParameters(
        command=args.server, args=["--only-text-feedback"], env=environment)
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=args.timeout)) as session:
            await session.initialize()
            if args.script:
                path = args.script.resolve()
                code = (f"exec(compile({path.read_text()!r}, {str(path)!r}, 'exec'), "
                        f"{{'__file__': {str(path)!r}, '__name__': '__main__'}})")
                result = await session.call_tool("execute_code", {
                    "code": code, "include_screenshot": False})
            else:
                result = await session.call_tool("get_rpc_status", {})
            if result.isError:
                raise RuntimeError(result.model_dump_json())
            for block in result.content:
                if block.type != "text":
                    continue
                # この実装は失敗時にもisError=falseでテキストを返す。
                if block.text.startswith(("Failed", "Error")):
                    raise RuntimeError(block.text)
                try:
                    body = json.loads(block.text)
                except ValueError:
                    body = None
                if isinstance(body, dict) and body.get("success") is False:
                    raise RuntimeError(block.text)
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())
