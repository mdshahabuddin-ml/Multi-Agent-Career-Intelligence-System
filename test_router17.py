from fastapi import FastAPI
from backend.api import jobs
from fastapi.routing import APIRoute

# Test 1: Add all routes manually
app = FastAPI()
router = jobs.router

print("Adding routes one by one...")
for i, route in enumerate(router.routes):
    new_route = APIRoute(
        path=router.prefix + route.path,
        endpoint=route.endpoint,
        methods=route.methods,
        response_model=route.response_model,
        status_code=route.status_code,
        tags=route.tags,
        dependencies=route.dependencies,
        summary=route.summary,
        description=route.description,
        response_description=route.response_description,
        responses=route.responses,
        deprecated=route.deprecated,
        operation_id=route.operation_id,
        response_class=route.response_class,
        name=route.name,
        include_in_schema=route.include_in_schema,
        callbacks=route.callbacks,
        openapi_extra=route.openapi_extra,
    )
    app.router.routes.append(new_route)
    print(f"Added route {i}: {router.prefix + route.path} - {len(app.routes)} routes")

print(f"\nTotal routes after manual add: {len(app.routes)}")
for r in app.routes:
    if hasattr(r, 'path'):
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")

# Also test include_router directly
print("\n--- Testing include_router directly ---")
app2 = FastAPI()
from backend.api import jobs
router = jobs.router

# Try with explicit prefix
app2.include_router(router, prefix="/api")
print(f"After include_router with prefix: {len(app2.routes)} routes")
for r in app2.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")