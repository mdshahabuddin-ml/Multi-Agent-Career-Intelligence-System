from fastapi import FastAPI
from backend.api import jobs, health

app = FastAPI()

print("Before include_router:")
print(f"  Routes: {len(app.routes)}")

app.include_router(health.router)
print(f"After health router: {len(app.routes)} routes")

# Debug: Check jobs router routes before including
print(f"\nJobs router routes count: {len(jobs.router.routes)}")
for r in jobs.router.routes:
    print(f"  {r.path} - {r.methods}")

app.include_router(jobs.router)
print(f"\nAfter jobs router: {len(app.routes)} routes")

for r in app.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f'  {r.path} - {getattr(r, "methods", "N/A")}')

# Also check if the routes are actually APIRoute objects
print("\nAll routes:")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f'  {r.path} - {type(r).__name__} - {getattr(r, "methods", "N/A")}')