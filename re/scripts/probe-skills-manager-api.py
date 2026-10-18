import json, urllib.request

u = "http://127.0.0.1:43129/api/dsh-skills-manager/state"
d = json.load(urllib.request.urlopen(u, timeout=10))["data"]
print("top keys:", list(d))
for root in d.get("roots", []):
    print(f"\n--- root {root['key']}  path={root['path']}")
    print(f"    exists={root['exists']} enabled={root['enabled']} skills={len(root.get('skills', []))}")
    for sk in root.get("skills", [])[:8]:
        if isinstance(sk, dict):
            print("     *", {k: sk.get(k) for k in ("name", "enabled", "description", "path") if k in sk})
print("\npolicy enabledSkills:", json.dumps(d.get("enabledSkills"), ensure_ascii=False)[:300])
print("policy disabledSkills:", json.dumps(d.get("disabledSkills"), ensure_ascii=False)[:300])
