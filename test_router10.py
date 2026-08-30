from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()

print("app.routes:", len(app.routes))
print("app.router.routes:", len(app.router.routes))
print("app is app.router:", app is app.router)

router = jobs.router

# Include router
app.include_router(router)

print("\nAfter include_router:")
print(f"app.routes: {len(app.routes)}")
print(f"app.router.routes: {len(app.router.routes)}")

for r in app.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")