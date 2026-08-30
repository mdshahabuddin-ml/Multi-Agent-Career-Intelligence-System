from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()

# Check what include_router does internally
router = jobs.router

print("Router routes before include:", len(router.routes))
for r in router.routes:
    print(f"  {r.path} - {r.methods}")

# Let's trace what happens
print("\nCalling include_router...")
app.include_router(router)

print(f"\nApp routes after include: {len(app.router.routes)}")
for r in app.router.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {type(r).__name__} - {getattr(r, 'methods', 'N/A')}")