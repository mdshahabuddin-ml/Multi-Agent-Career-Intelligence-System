from fastapi import FastAPI
from backend.api import jobs
import traceback

app = FastAPI()

router = jobs.router

print("Before include_router:")
print(f"  app.routes: {len(app.routes)}")
print(f"  router.routes: {len(router.routes)}")

# Try with try/except to catch any errors
try:
    app.include_router(router)
    print("include_router succeeded")
except Exception as e:
    print(f"Error during include_router: {e}")
    traceback.print_exc()

print(f"\nAfter include_router:")
print(f"  app.routes: {len(app.routes)}")
print(f"  app.router.routes: {len(app.router.routes)}")

# Let's also check if there's an exception handler that might be catching errors
import fastapi
from fastapi.routing import APIRouter

# Let's manually call the internal method
from fastapi import FastAPI
from fastapi.routing import APIRoute

# Check if there's a validation error
print("\nTrying to manually add routes...")
from backend.api import jobs
router = jobs.router

app2 = FastAPI()
for route in jobs.router.routes:
    try:
        app2.router.routes.append(route)
        print(f"Added: {route.path}")
    except Exception as e:
        print(f"Error adding {route.path}: {e}")

print(f"\nManual add result: {len(app2.routes)} routes")
for r in app2.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")