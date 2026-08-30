from backend.database import Base, engine
from backend.models import (
    User,
    Profile,
    Skill,
    Project,
    Experience,
)


def init_database():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_database()
    print("Database tables created successfully.")