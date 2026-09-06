"""Fusion組み込みMCPへのローカルHTTPクライアント。Fusionを起動して使う。"""

import argparse
import json
from pathlib import Path
import urllib.request


class FusionMCP:
    def __init__(self, url="http://127.0.0.1:27182/mcp", timeout=30):
        self.url, self.timeout, self.sequence = url, timeout, 0
        self.headers = {"Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream"}
        self.initialization = self.request("initialize", {
            "protocolVersion": "2025-03-26", "capabilities": {},
            "clientInfo": {"name": "dgx-rack-codex", "version": "1.0.0"}})
        self.headers["MCP-Protocol-Version"] = self.initialization["protocolVersion"]
        self.request("notifications/initialized", notification=True)

    def request(self, method, params=None, notification=False):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notification:
            self.sequence += 1
            payload["id"] = self.sequence
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
                                     headers=self.headers, method="POST")
        message = None
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            session = response.headers.get("Mcp-Session-Id")
            if session:
                self.headers["Mcp-Session-Id"] = session
            if notification:
                return None
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                data_lines = []
                for raw in response:
                    line = raw.decode().rstrip("\r\n")
                    if line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())
                    elif not line and data_lines:
                        item = json.loads("\n".join(data_lines))
                        data_lines = []
                        if item.get("id") == self.sequence:
                            message = item
                            break
            else:
                message = json.loads(response.read())
        if message is None:
            raise RuntimeError("MCPから要求に対応する応答が届きませんでした。")
        if "error" in message:
            raise RuntimeError(json.dumps(message["error"], ensure_ascii=False))
        return message["result"]

    def call(self, name, arguments):
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise RuntimeError(json.dumps(result, ensure_ascii=False))
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    body = json.loads(block["text"])
                except (ValueError, KeyError):
                    continue
                if isinstance(body, dict) and body.get("success") is False:
                    raise RuntimeError(json.dumps(body, ensure_ascii=False))
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:27182/mcp")
    parser.add_argument("--timeout", type=float, default=30)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    call = commands.add_parser("call")
    call.add_argument("tool")
    call.add_argument("arguments", type=Path, help="引数を記載したJSONファイル")
    script = commands.add_parser("script")
    script.add_argument("path", type=Path, help="def run(_context: str)を持つPythonファイル")
    args = parser.parse_args()
    client = FusionMCP(args.url, timeout=args.timeout)
    if args.command == "list":
        result = client.request("tools/list", {})
    elif args.command == "call":
        result = client.call(args.tool, json.loads(args.arguments.read_text()))
    else:
        result = client.call("fusion_mcp_execute", {
            "featureType": "script", "object": {"script": args.path.read_text()}})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
