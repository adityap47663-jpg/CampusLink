from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path

from app.api import deps
from app.core import security
from app.db.session import get_db
from app.models.models import User as UserModel
from app.schemas.user import User, UserCreate, UserUpdate

router = APIRouter()

@router.post("/", response_model=User)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserCreate,
    invite_code: Optional[str] = None
) -> Any:
    """
    Create new user.
    """
    result = await db.execute(select(UserModel).where(UserModel.email == user_in.email))
    user = result.scalar_one_or_none()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    college_id = None
    if invite_code:
        from app.models.models import College
        res = await db.execute(select(College).where(College.invite_code == invite_code))
        college = res.scalar_one_or_none()
        if not college:
            raise HTTPException(status_code=400, detail="Invalid invite code")
        college_id = college.id

    db_obj = UserModel(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_superuser=user_in.is_superuser,
        college_id=college_id,
        role="student" if not user_in.is_superuser else "super_admin"
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[User])
async def read_users(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(deps.get_current_active_college_admin),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve users (filtered by college for college admins).
    """
    query = select(UserModel)
    if not current_user.is_superuser:
        query = query.where(UserModel.college_id == current_user.college_id)
        
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/me", response_model=User)
async def read_user_me(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user with stats.
    """
    from app.models.models import Participation

    # Count events the user has joined
    evt_stmt = select(func.count(Participation.id)).where(Participation.user_id == current_user.id)
    evt_count = await db.execute(evt_stmt)
    current_user.events_count = evt_count.scalar() or 0

    # buddies_count: count of distinct other users who attended the same events
    # build a subquery for all event IDs the current user participated in
    subq = select(Participation.event_id).where(Participation.user_id == current_user.id).subquery()
    buddy_stmt = (
        select(func.count(func.distinct(Participation.user_id)))
        .where(Participation.event_id.in_(subq))
        .where(Participation.user_id != current_user.id)
    )
    buddy_count = await db.execute(buddy_stmt)
    current_user.buddies_count = buddy_count.scalar() or 0

    # persist the counters (optional caching/storage)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return current_user

@router.put("/me", response_model=User)
async def update_user_me(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: UserUpdate,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user profile.
    """
    update_data = user_in.dict(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = security.get_password_hash(update_data["password"])
        del update_data["password"]
    
    for field in update_data:
        setattr(current_user, field, update_data[field])
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/me/profile-image", response_model=User)
async def upload_profile_image(
    *,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a profile image for the current user.
    Uploaded to: users/{user_id}/profile_picture/{filename}
    """
    from app.utils.storage import storage
    
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG/PNG/WEBP allowed.")
    
    # Read file content
    contents = await file.read()
    
    # Try to upload to Supabase
    image_url = storage.upload_profile_image(
        user_id=current_user.id,
        file_path=file.filename,
        file_content=contents
    )
    
    # Fallback to local storage if Supabase is not configured
    if image_url is None:
        upload_dir = Path("static/profile_images")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"user_{current_user.id}.{file_extension}"
        file_path = upload_dir / file_name
        with file_path.open("wb") as buffer:
            buffer.write(contents)
        image_url = f"/static/profile_images/{file_name}"
    
    current_user.profile_image_url = image_url
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/join-college")
async def join_college(
    *,
    db: AsyncSession = Depends(get_db),
    invite_code: str,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Join a college using an invite code.
    """
    from app.models.models import College
    res = await db.execute(select(College).where(College.invite_code == invite_code))
    college = res.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=400, detail="Invalid invite code")
    
    current_user.college_id = college.id
    current_user.college_name = college.name 
    db.add(current_user)
    await db.commit()
    return {"message": f"Successfully joined {college.name}"}

@router.delete("/{id}")
async def delete_user(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a user by ID.
    - Super Admin can delete any user.
    - Users can delete their own account.
    """
    if not current_user.is_superuser and current_user.id != id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    result = await db.execute(select(UserModel).where(UserModel.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}
