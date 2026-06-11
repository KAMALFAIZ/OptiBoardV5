import urllib.request, urllib.error, json

# Voir exactement ce que retourne le GET sur /drilldown
url = "http://127.0.0.1:8084/api/datasources/unified/DS_CA_DETAIL_COMPLET/drilldown"
req = urllib.request.Request(url, method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode('utf-8', errors='replace')
        print(f"GET HTTP {resp.status}")
        print(f"Content-Type: {resp.headers.get('content-type')}")
        print(f"Body (300 chars): {body[:300]}")
except urllib.error.HTTPError as e:
    print(f"GET: HTTP {e.code}")
    body = e.read().decode('utf-8', errors='replace')
    print(f"Body: {body[:200]}")

print()

# Voir les routes chargées - chercher si drilldown est dans OpenAPI
url2 = "http://127.0.0.1:8084/openapi.json"
req = urllib.request.Request(url2, method='GET')
with urllib.request.urlopen(req, timeout=5) as resp:
    schema = json.loads(resp.read())
    paths = schema.get('paths', {})
    ds_routes = {k: list(v.keys()) for k, v in paths.items() if 'datasource' in k.lower() or 'unified' in k.lower()}
    print("Routes /datasources dans OpenAPI:")
    for p, m in sorted(ds_routes.items()):
        print(f"  {m} {p}")

# Vérifier quel processus Python tourne sur 8084
import subprocess
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if ':8084' in line and 'LISTENING' in line:
        pid = line.strip().split()[-1]
        print(f"\nPID sur 8084: {pid}")
        # Obtenir le chemin du process
        result2 = subprocess.run(['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'CommandLine'], capture_output=True, text=True)
        print(f"Commande: {result2.stdout.strip()[:300]}")
        break
