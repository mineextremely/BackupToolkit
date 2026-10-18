import json
import os
import subprocess

env = dict(os.environ)
env["REA_JADX_MCP_JAR"] = os.path.expandvars(r"%LOCALAPPDATA%\rea-tools\jadx-headless-mcp-0.7.1-all.jar")
env["REA_APKTOOL_COMMAND"] = os.path.expandvars(r"%LOCALAPPDATA%\rea-tools\apktool.cmd")

raw = subprocess.run(
    ["cmd.exe", "/d", "/c", "npx", "-y", "rea-agents@latest", "doctor", "--client", "dsh", "--json"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
).stdout
d = json.loads(raw[raw.find("{"):])

print("healthy:", d.get("healthy"))
for c in d.get("checks", []):
    print(f"  {c['name']:16s} ok={str(c['ok']):5s} {c.get('classification')}  {str(c.get('detail'))[:140]}")

for prov in d.get("providerInspections", []):
    if prov.get("id") != "jadx":
        continue
    print("\n--- jadx providerInspection ---")
    print(json.dumps(prov, ensure_ascii=False, indent=2)[:5000])
