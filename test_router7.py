from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()

# Try include_router with explicit prefix
app.include_router(jobs.router, prefix="/jobs")

print(f"After include_router with prefix: {len(app.routes)} routes")
for r in app.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")

# Also try without prefix (since router already has prefix)
app2 = FastAPI()
app2.include_router(jobs.router)  # router already has prefix="/jobs"
print(f"\nWithout explicit prefix: {len(app2.routes)} routes")
for r in app2.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")