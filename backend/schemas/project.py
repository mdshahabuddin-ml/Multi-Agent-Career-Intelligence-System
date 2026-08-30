from pydantic import BaseModel


class ProjectCreate(BaseModel):

    name: str

    description: str | None = None

    technologies: str | None = None

    url: str | None = None


class ProjectResponse(ProjectCreate):

    id: int

    profile_id: int

    model_config = {
        "from_attributes": True,
    }