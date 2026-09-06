"""Fusionの正本をMCPで検査・出力する。寸法はF3D内で管理する。"""

import argparse
import json
from pathlib import Path

from fusion_mcp import FusionMCP


ROOT = Path(__file__).resolve().parents[1]


def execute(client, statement):
    script=("import sys, importlib\n"
            f"sys.path.insert(0,{str(ROOT/'scripts')!r})\n"
            "import fusion_rack\n"
            "def run(_context: str):\n"
            "    importlib.reload(fusion_rack)\n"
            f"    {statement}\n")
    result=client.call("fusion_mcp_execute",{"featureType":"script","object":{"script":script}})
    for block in result.get("content",[]):
        if block.get("type")=="text":
            body=json.loads(block["text"])
            print(body.get("message",block["text"]),end="",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["validate","style","export","previews","roundtrip"])
    parser.add_argument("--url",default="http://127.0.0.1:27182/mcp")
    parser.add_argument("--timeout",type=float,default=120)
    args=parser.parse_args()
    client=FusionMCP(args.url,args.timeout)
    execute(client,f"fusion_rack.{args.command}()")


if __name__=="__main__":
    main()
