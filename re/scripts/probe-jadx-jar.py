"""Probe the JADX MCP jar's stdio protocol directly (no REA involved)."""
import json
import os
import subprocess
import threading
import time

jar = os.path.expandvars(r"%LOCALAPPDATA%\rea-tools\jadx-headless-mcp-0.7.1-all.jar")
print("jar:", jar, os.path.getsize(jar))

p = subprocess.Popen(
    ["java", "-jar", jar],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace", bufsize=1,
)

lines, errs = [], []


def rd():
    for line in p.stdout:
        lines.append(line)


def rde():
    for line in p.stderr:
        errs.append(line)


threading.Thread(target=rd, daemon=True).start()
threading.Thread(target=rde, daemon=True).start()

msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
       "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                  "clientInfo": {"name": "jar-probe", "version": "0"}}}
p.stdin.write(json.dumps(msg) + "\n")
p.stdin.flush()

end = time.time() + 90
while time.time() < end and not lines:
    time.sleep(0.3)

print("--- stdout lines:", len(lines))
for line in lines[:3]:
    print(line[:600])
print("--- stderr lines:", len(errs))
for line in errs[:8]:
    print(line.rstrip()[:300])

# try tools/list if initialize answered
if lines:
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n")
    p.stdin.flush()
    end = time.time() + 60
    while time.time() < end and len(lines) < 2:
        time.sleep(0.3)
    for line in lines[1:2]:
        try:
            d = json.loads(line)
            tools = d.get("result", {}).get("tools", [])
            print("TOOL COUNT:", len(tools), [t.get("name") for t in tools][:12])
        except Exception as e:
            print("parse:", e, line[:400])

p.terminate()
try:
    p.wait(timeout=10)
except Exception:
    p.kill()
