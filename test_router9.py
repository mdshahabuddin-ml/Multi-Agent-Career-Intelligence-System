from fastapi import FastAPI
from backend.api import jobs

app = FastAPI()

router = jobs.router

# Let's manually trace what include_router does
# From FastAPI source, include_router does:
# 1. For each route in router.routes:
#    - Create a new route with updated path (prefix + route.path)
#    - Add to app.router.routes

# Let's manually do what include_router does
from fastapi.routing import APIRoute

print("Adding routes manually...")
for route in jobs.router.routes:
    # This is what include_router does internally
    new_route = APIRoute(
        path=jobs.router.prefix + route.path,
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

print(f"After manual add: {len(app.router.routes)} routes")
for r in app.router.routes:
    if hasattr(r, 'path') and 'jobs' in r.path:
        print(f"  {r.path} - {getattr(r, 'methods', 'N/A')}")