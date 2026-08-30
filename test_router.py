from fastapi import FastAPI
from backend.api import jobs, health

app = FastAPI()

print("Before include_router:")
print(f"  Routes: {len(app.routes)}")

app.include_router(health.router)
print(f"After health router: {len(app.routes)} routes")

app.include_router(jobs.router)
print(f"After jobs router: {len(app.routes)} routes")

for r in app.routes:
    if hasattr(r, 'path'):
        print(f'  {r.path} - {getattr(r, "methods", "N/A")}')