from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()

# Manually add routes from jobs router
for route in jobs.router.routes:
    app.router.routes.append(route)

print(f"After manual add: {len(app.routes)} routes")
for r in app.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")