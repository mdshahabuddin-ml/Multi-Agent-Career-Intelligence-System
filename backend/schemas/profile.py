from pydantic import BaseModel
from pydantic import Field


class ProfileCreate(BaseModel):

    headline: str | None = None

    target_role: str | None = None

    location: str | None = None

    bio: str | None = None

    years_of_experience: int = Field(
        default=0,
        ge=0,
    )


class ProfileUpdate(ProfileCreate):
    pass


class ProfileResponse(ProfileCreate):

    id: int

    user_id: int

    model_config = {
        "from_attributes": True,
    }