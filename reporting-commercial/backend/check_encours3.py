import sys, os, urllib.request, urllib.error, json

# Tester avec GET pour voir les méthodes autorisées
url = "http://127.0.0.1:8084/api/datasources/unified/DS_CA_DETAIL_COMPLET/drilldown"

# Test GET
req = urllib.request.Request(url, method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"GET: HTTP {resp.status}")
except urllib.error.HTTPError as e:
    print(f"GET: HTTP {e.code} - Allow: {e.headers.get('Allow', 'N/A')}")

# Test OPTIONS
req = urllib.request.Request(url, method='OPTIONS')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"OPTIONS: HTTP {resp.status} - Allow: {resp.headers.get('Allow', 'N/A')}")
except urllib.error.HTTPError as e:
    print(f"OPTIONS: HTTP {e.code} - Allow: {e.headers.get('Allow', 'N/A')}")
    body = e.read().decode('utf-8', errors='replace')
    print(f"  Body: {body[:300]}")

# Test l'URL sans /drilldown
url2 = "http://127.0.0.1:8084/api/datasources/unified/DS_CA_DETAIL_COMPLET"
req = urllib.request.Request(url2, method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
        print(f"\nGET unified (sans drilldown): HTTP 200 - success={data.get('success')}")
except urllib.error.HTTPError as e:
    print(f"\nGET unified (sans drilldown): HTTP {e.code}")

# Lister toutes les routes du backend
url3 = "http://127.0.0.1:8084/api/docs"
req = urllib.request.Request(url3, method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print(f"\nDocs: HTTP {resp.status} (backend accessible)")
except Exception as e:
    print(f"\nDocs: {e}")

# Vérifier via openapi.json
url4 = "http://127.0.0.1:8084/openapi.json"
req = urllib.request.Request(url4, method='GET')
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        schema = json.loads(resp.read())
        paths = schema.get('paths', {})
        drilldown_routes = {k: v for k, v in paths.items() if 'drilldown' in k}
        print(f"\nRoutes /drilldown dans OpenAPI:")
        for path, methods in drilldown_routes.items():
            print(f"  {path}: {list(methods.keys())}")
except Exception as e:
    print(f"\nOpenAPI: {e}")
