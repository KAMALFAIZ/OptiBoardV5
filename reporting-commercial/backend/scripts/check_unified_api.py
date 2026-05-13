"""Check what the unified preview API returns in the columns field."""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')

# Call the API directly
url = 'http://127.0.0.1:8084/api/datasources/unified/DS_FACTURES/preview'
payload = json.dumps({'context': {'dateDebut': '2024-01-01', 'dateFin': '2026-05-09'}, 'limit': 3}).encode()

req = urllib.request.Request(url, data=payload, headers={
    'Content-Type': 'application/json',
    'X-DWH-Code': 'KA',
    'Authorization': 'Bearer fake'  # will likely fail auth
})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read())
        print("columns:", json.dumps(body.get('columns', []), indent=2))
except Exception as e:
    print(f"Error: {e}")
