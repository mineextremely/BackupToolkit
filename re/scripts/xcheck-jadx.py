"""Independent cross-check with jadx-headless-mcp 0.7.1's own MCP tools (bypasses REA's spawn)."""
import json
import os
import subprocess
import threading
import time

JAR = os.path.expandvars(r"%LOCALAPPDATA%\rea-tools\jadx-headless-mcp-0.7.1-all.jar")
APK = r"D:\GITS\BackupToolkit-REA\BackupToolkit v1.1.1.apk"

p = subprocess.Popen(["java", "-jar", JAR], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", bufsize=1)
out = []


def rd():
    for line in p.stdout:
        out.append(line)


threading.Thread(target=rd, daemon=True).start()
_id = [0]


def call(method, params):
    _id[0] += 1
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": _id[0], "method": method, "params": params}) + "\n")
    p.stdin.flush()
    end = time.time() + 300
    while time.time() < end:
        for line in out:
            try:
                m = json.loads(line)
            except Exception:
                continue
            if m.get("id") == _id[0]:
                return m
        time.sleep(0.2)
    return None


def call_tool(name, args, timeout=600):
    r = call("tools/call", {"name": name, "arguments": args})
    if not r:
        return None
    if "error" in r:
        return {"__error__": r["error"]}
    content = r.get("result", {}).get("content", [])
    for c in content:
        if c.get("type") == "text":
            try:
                return json.loads(c["text"])
            except Exception:
                return c["text"]
    return r.get("result")


print("init:", call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                   "clientInfo": {"name": "xcheck", "version": "0"}}) is not None)
p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}) + "\n")

tools = call("tools/list", {})["result"]["tools"]
print("tools:", len(tools))
print("names:", [t["name"] for t in tools])

print("\n-- load_apk --")
print(call_tool("load_apk", {"path": APK}, timeout=900))

print("\n-- get_app_info --")
print(json.dumps(call_tool("get_app_info", {}), ensure_ascii=False)[:800])

print("\n-- list_classes (search 'while') --")
res = call_tool("list_classes", {"filter": "while"}) if tools else None
print(json.dumps(res, ensure_ascii=False)[:1200])

p.terminate()
try:
    p.wait(timeout=10)
except Exception:
    p.kill()
