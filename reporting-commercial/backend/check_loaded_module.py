import sys, os
sys.path.insert(0, '.')
import importlib.util

spec = importlib.util.find_spec('app.routes.etl_tables')
print(f"Module resolves to: {spec.origin if spec else 'NOT FOUND'}")

# Check dist_client
dc_routes = os.path.join('dist_client', 'app', 'routes')
if os.path.isdir(dc_routes):
    files = [f for f in os.listdir(dc_routes) if 'etl_tables' in f]
    print(f"dist_client/app/routes/ etl_tables files: {files}")

# Check if dist_client has __init__.py that might shadow
dc_app = os.path.join('dist_client', 'app')
if os.path.isdir(dc_app):
    inits = [f for f in os.listdir(dc_app) if '__init__' in f]
    print(f"dist_client/app/ init files: {inits}")

# Critical: check if run.py adds dist_client to path
with open('run.py', 'r') as f:
    for i, line in enumerate(f, 1):
        if 'dist_client' in line.lower() or 'sys.path' in line.lower():
            print(f"run.py:{i}: {line.rstrip()}")

# Check app/__init__.py for path manipulation
app_init = os.path.join('app', '__init__.py')
if os.path.exists(app_init):
    with open(app_init) as f:
        content = f.read()
    if content.strip():
        print(f"\napp/__init__.py content ({len(content)} chars):")
        print(content[:500])
    else:
        print("app/__init__.py is empty")

# Check app/routes/__init__.py
routes_init = os.path.join('app', 'routes', '__init__.py')
if os.path.exists(routes_init):
    with open(routes_init) as f:
        content = f.read()
    if content.strip():
        print(f"\napp/routes/__init__.py content ({len(content)} chars):")
        print(content[:500])
    else:
        print("app/routes/__init__.py is empty")
