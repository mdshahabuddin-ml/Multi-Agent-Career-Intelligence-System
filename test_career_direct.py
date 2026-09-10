import traceback
from backend.database import SessionLocal
from backend.services.career_service import CareerService

db = SessionLocal()
try:
    service = CareerService(db)
    result = service.assess_career(
        user_id=5,
        current_role="Software Engineer",
        years_experience=5,
        skills=[],
        target_role="Senior Software Engineer",
    )
    print(f"OK: score={result.overall_score}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
finally:
    db.close()
