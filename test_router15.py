from fastapi import FastAPI
from backend.api import jobs
import sys

app = FastAPI()
router = jobs.router

# Patch include_router to see what happens
original_include = FastAPI.include_router

def traced_include(self, router, *args, **kwargs):
    print(f"include_router called with router: {router}, prefix={kwargs.get('prefix')}")
    try:
        result = original_include(self, router, *args, **kwargs)
        print(f"include_router returned: {result}")
        return result
    except Exception as e:
        print(f"Exception in include_router: {e}")
        import traceback
        traceback.print_exc()
        raise

FastAPI.include_router = traced_include

app = FastAPI()
router = jobs.router

print("Before include_router:")
print(f"  app.routes: {len(app.routes)}")

try:
    app.include_router(router)
    print("include_router returned successfully")
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

print(f"\nAfter include_router:")
print(f"  app.routes: {len(app.routes)}")
print(f"  app.router.routes: {len(app.router.routes)}")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {type(r).__name__}")