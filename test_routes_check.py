from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()
app.include_router(jobs.router)

print("Routes:")
for r in app.routes:
    print(f"  {type(r).__name__}: {getattr(r, 'path', 'N/A')}")

print()
print("app.router.routes:")
for r in app.router.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {type(r).__name__}")
    else:
        print(f"  {type(r).__name__}: {getattr(r, 'original_router', 'N/A')}")

print()
print("Included routers:")
for r in app.router.routes:
    if hasattr(r, 'original_router'):
        print(f"  Included router: {r.original_router}")
        print(f"  Routes in included: {len(r.original_router.routes)}")
        for route in r.original_router.routes:
            print(f"    {route.path} - {route.methods}")