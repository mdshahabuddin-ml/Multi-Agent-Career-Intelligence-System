from fastapi import FastAPI, APIRouter

# Create a simple router
test_router = APIRouter(prefix="/test")
@test_router.get("/hello")
async def hello():
    return {"message": "Hello"}

@test_router.get("/world")
async def world():
    return {"message": "World"}

app = FastAPI()

print("Before include_router:")
print(f"  Routes: {len(app.routes)}")

app.include_router(test_router)
print(f"After test router: {len(app.routes)} routes")

for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")

# Now test with the jobs router
from backend.api import jobs

app2 = FastAPI()
app2.include_router(jobs.router)
print(f"\nAfter jobs router: {len(app2.routes)} routes")
for r in app2.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")