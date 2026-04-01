"""Test du login avec urllib"""
import urllib.request
import json

try:
    data = json.dumps({"username": "superadmin", "password": "admin"}).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:8080/api/users/login',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        print(f"Status: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Erreur: {e}")
