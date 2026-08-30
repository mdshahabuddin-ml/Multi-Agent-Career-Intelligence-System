from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()

print("FastAPI version:", __import__('fastapi').__version__)

router = jobs.router

# Check what include_router does by looking at source
import fastapi
print("FastAPI file:", fastapi.__file__)

# Let's manually trace include_router
print("\nBefore include_router:")
print(f"  app.routes: {len(app.routes)}")
print(f"  app.router.routes: {len(app.router.routes)}")

# Call include_router
app.include_router(router)

print("\nAfter include_router:")
print(f"  app.routes: {len(app.routes)}")
print(f"  app.router.routes: {len(app.router.routes)}")

# Check if routes were added to the router
print("\napp.router.routes:")
for r in app.router.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {type(r).__name__}")

print("\napp.routes:")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {type(r).__name__}")