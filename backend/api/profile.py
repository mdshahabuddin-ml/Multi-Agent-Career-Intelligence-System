from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api import auth
from backend.models.profile import Profile
from backend.models.user import User
from backend.schemas.profile import (
    ProfileCreate, ProfileUpdate, ProfileResponse
)

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get current user's profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if not profile:
        # Create empty profile if doesn't exist
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    return profile


@router.post("/me", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    profile_data: ProfileCreate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create profile for current user."""
    existing = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PATCH to update."
        )
    
    profile = Profile(user_id=current_user.id, **profile_data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    return profile


@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    updates: ProfileUpdate,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
    
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(profile)
    
    return profile


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete current user's profile."""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    db.delete(profile)
    db.commit()


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_user_profile(
    user_id: int,
    current_user = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get another user's profile (public view)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        # Return basic profile with user info
        return ProfileResponse(
            id=0,
            user_id=user_id,
            headline=None,
            target_role=None,
            location=None,
            bio=None,
            years_of_experience=0,
        )
    
    return profile