from fastapi import FastAPI
from backend.api import jobs
import fastapi

app = FastAPI()
router = jobs.router

# Let's manually trace what include_router does
# From FastAPI source, include_router does:
# 1. For each route in router.routes:
#    - Create a new route with updated path (prefix + route.path)
#    - Add to self.router.routes

# Let's manually step through
print("Router routes:", len(router.routes))
for r in router.routes:
    print(f"  {r.path} - {r.methods}")

# Check if there's a prefix conflict
print(f"\nRouter prefix: '{router.prefix}'")

# Check if there's a prefix conflict with existing routes
# FastAPI might be checking for conflicts
print("\nExisting routes in app:")
for r in app.routes:
    print(f"  {r.path}")

# Try to manually add one route
from fastapi.routing import APIRoute

app2 = FastAPI()
route = router.routes[0]
print(f"\nTrying to add route: {route.path}")

# This is what include_router does internally
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

app2 = FastAPI()
app2.router.routes.append(new_route)
print(f"Manual add result: {len(app2.routes)} routes")

# Now try the actual include_router
app2 = FastAPI()
print("Calling include_router...")
try:
    app2.include_router(router)
    print(f"Success! Routes: {len(app2.routes)}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()