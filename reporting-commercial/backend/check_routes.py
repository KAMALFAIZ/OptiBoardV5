import urllib.request
resp = urllib.request.urlopen('http://127.0.0.1:8084/api/openapi.json')
content = resp.read()
print(f"Status: {resp.status}")
print(f"Content-Type: {resp.headers.get('Content-Type')}")
print(f"Length: {len(content)}")
print(f"First 200 bytes: {content[:200]}")
