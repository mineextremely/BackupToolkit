"""Pre-flight: prove the exact command in cordis.patch.yml yields MCP tools.

Speaks MCP over stdio to `npx -y rea-agents@6.5.0 mcp` using newline-delimited
JSON-RPC, performs initialize -> initialized -> tools/list, and prints the tool
count plus a few names. Read-only: never calls a tool.
"""
import json
import subprocess
import sys
import threading
import time

CMD = ["cmd.exe", "/d", "/c", "npx", "-y", "rea-agents@6.5.0", "mcp"]

p = subprocess.Popen(
    CMD,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1,
)

lines = []


def reader():
    for line in p.stdout:
        lines.append(line.rstrip("\n"))


threading.Thread(target=reader, daemon=True).start()


def send(obj):
    p.stdin.write(json.dumps(obj) + "\n")
    p.stdin.flush()


def wait_for(pred, timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        for line in list(lines):
            if not line.strip():
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue
            if pred(msg):
                return msg
        time.sleep(0.2)
    return None


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05",
                 "capabilities": {},
                 "clientInfo": {"name": "rea-preflight", "version": "0"}}})
init = wait_for(lambda m: m.get("id") == 1)
if not init:
    print("NO INITIALIZE RESPONSE")
    print("stderr:", p.stderr.read()[:2000] if p.stderr else "")
    sys.exit(1)

si = init.get("result", {}).get("serverInfo", {})
print("serverInfo:", si)
print("protocolVersion:", init.get("result", {}).get("protocolVersion"))
caps = init.get("result", {}).get("capabilities", {})
print("capability keys:", sorted(caps))

send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
tl = wait_for(lambda m: m.get("id") == 2)
if not tl:
    print("NO TOOLS/LIST RESPONSE")
    sys.exit(1)

tools = tl.get("result", {}).get("tools", [])
print("TOOL COUNT:", len(tools))
names = [t.get("name") for t in tools]
for probe in ["open_binary", "inspect_android_package", "inspect_android_method",
              "trace_android_references", "inspect_artifact", "decode_android_resources",
              "binary_session", "close_binary"]:
    print(f"  {probe:28s} {'present' if probe in names else 'MISSING'}")

p.terminate()
try:
    p.wait(timeout=10)
except Exception:
    p.kill()
