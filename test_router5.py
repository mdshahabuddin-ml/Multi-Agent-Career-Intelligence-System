from backend.api import jobs
import fastapi

router = jobs.router

print("Router type:", type(router))
print("Is APIRouter:", isinstance(router, fastapi.APIRouter))
print("Router routes:", len(router.routes))
print("Router prefix:", router.prefix)
print("Router tags:", router.tags)

# Check if it's a proper APIRouter
print("\nMRO:", [c.__name__ for c in type(router).__mro__])

# Check if routes are APIRoute objects
from fastapi.routing import APIRoute
for i, r in enumerate(router.routes):
    print(f"Route {i}: type={type(r).__name__}, is_APIRoute={isinstance(r, APIRoute)}")