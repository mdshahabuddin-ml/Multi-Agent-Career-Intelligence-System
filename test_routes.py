from backend.main import app

print("Total routes:", len(app.routes))
for r in app.routes:
    if hasattr(r, 'path'):
        print(f'  {r.path} - {getattr(r, "methods", "N/A")}')