"""Probe REA's ReaJadxBridge.java via the same argv REA uses, over stdio."""
import json
import os
import subprocess
import threading
import time

jar = os.path.expandvars(r"%LOCALAPPDATA%\rea-tools\jadx-headless-mcp-0.7.1-all.jar")
bridge = os.path.expandvars(
    r"C:\Users\NANO\AppData\Local\npm-cache\_npx\ad9a3fdbcad992c6\node_modules\rea-agents\bridge\android\ReaJadxBridge.java"
)
print("bridge:", os.path.exists(bridge), os.path.getsize(bridge))

p = subprocess.Popen(
    ["java", "--class-path", jar, bridge],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8", errors="replace", bufsize=1,
)
out, err = [], []


def rd(stream, sink):
    for line in stream:
        sink.append(line)


threading.Thread(target=rd, args=(p.stdout, out), daemon=True).start()
threading.Thread(target=rd, args=(p.stderr, err), daemon=True).start()

msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
       "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                  "clientInfo": {"name": "bridge-probe", "version": "0"}}}
p.stdin.write(json.dumps(msg) + "\n")
p.stdin.flush()

end = time.time() + 120
while time.time() < end and not out:
    if p.poll() is not None and not out:
        break
    time.sleep(0.3)

print("exit_code:", p.poll())
print("stdout lines:", len(out))
for line in out[:2]:
    print(line[:400])
print("stderr lines:", len(err))
for line in err[:5]:
    print("  E:", line.rstrip()[:200])

if out:
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}) + "\n")
    p.stdin.flush()
    end = time.time() + 90
    while time.time() < end and len(out) < 2:
        time.sleep(0.3)
    for line in out[1:2]:
        try:
            d = json.loads(line)
            names = [t.get("name") for t in d.get("result", {}).get("tools", [])]
            print("BRIDGE TOOLS:", len(names), names[:14])
        except Exception as e:
            print("parse err:", e, line[:300])

p.terminate()
try:
    p.wait(timeout=10)
except Exception:
    p.kill()
