import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.database_unified import get_central_connection

conn = get_central_connection()
cur = conn.cursor()

# Vérifier les datasources drilldown
for code in ['DS_CA_DETAIL_COMPLET', 'DS_ECHEANCES_NON_REGLEES']:
    cur.execute("SELECT code, nom, LEFT(query_template, 300) FROM APP_DataSources_Templates WHERE code=?", (code,))
    r = cur.fetchone()
    if r:
        print(f"OK: {r[0]} - {r[1]}")
        print(f"  Query: {r[2]}")
    else:
        print(f"MANQUANT: {code}")
    print()

conn.close()

# Tester si la route /drilldown repond
import urllib.request, urllib.error
import json

headers = {'Content-Type': 'application/json', 'X-DWH-Code': 'SG'}
body = json.dumps({"page": 1, "pageSize": 5, "context": {}}).encode()

for code in ['DS_CA_DETAIL_COMPLET', 'DS_ECHEANCES_NON_REGLEES']:
    url = f"http://127.0.0.1:8084/api/datasources/unified/{code}/drilldown"
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"POST {code}: HTTP 200 - success={data.get('success')}")
    except urllib.error.HTTPError as e:
        print(f"POST {code}: HTTP {e.code} {e.reason}")
    except Exception as e:
        print(f"POST {code}: ERROR {e}")
