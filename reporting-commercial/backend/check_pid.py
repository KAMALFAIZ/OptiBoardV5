import urllib.request, json, os

# Voir quelle version du backend tourne
url = "http://127.0.0.1:8084/api/docs"
req = urllib.request.Request(url, method='GET')
with urllib.request.urlopen(req, timeout=5) as resp:
    body = resp.read().decode('utf-8', errors='replace')
    print("Docs accessible:", 'swagger' in body.lower() or 'openapi' in body.lower())

# Compter les routes drilldown
url2 = "http://127.0.0.1:8084/openapi.json"
req = urllib.request.Request(url2, method='GET')
with urllib.request.urlopen(req, timeout=5) as resp:
    schema = json.loads(resp.read())
    paths = schema.get('paths', {})
    drilldown = [k for k in paths if 'drilldown' in k]
    unified = [k for k in paths if 'unified' in k]
    print(f"Routes drilldown: {len(drilldown)} -> {drilldown}")
    print(f"Routes unified: {len(unified)} -> {unified}")

# Chercher le PID sur 8084 et sa commande
import subprocess
r = subprocess.run('netstat -ano', shell=True, capture_output=True)
lines = r.stdout.decode('utf-8', errors='ignore').split('\n')
for l in lines:
    if ':8084' in l and 'LISTEN' in l:
        pid = l.strip().split()[-1]
        print(f"\nPID 8084: {pid}")
        r2 = subprocess.run(f'wmic process where ProcessId={pid} get ExecutablePath,CommandLine /format:list', shell=True, capture_output=True)
        print(r2.stdout.decode('utf-8', errors='ignore')[:500])
