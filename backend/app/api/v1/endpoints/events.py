from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.api import deps
from app.db.session import get_db
from app.models.models import Event as EventModel, User as UserModel, Notification as NotificationModel
from app.schemas.event import Event, EventCreate, EventUpdate
from app.websockets.manager import manager

router = APIRouter()

@router.get("/", response_model=List[Event])
async def read_events(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve events (filtered by college).
    """
    query = select(EventModel)
    if not current_user.is_superuser:
        query = query.where(EventModel.college_id == current_user.college_id)
        
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

@router.post("/", response_model=Event)
async def create_event(
    *,
    db: AsyncSession = Depends(get_db),
    event_in: EventCreate,
    current_user: UserModel = Depends(deps.get_current_active_college_admin),
) -> Any:
    """
    Create new event (College Admin only).
    """
    db_obj = EventModel(
        **event_in.dict(),
        organizer_id=current_user.id,
        college_id=current_user.college_id
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    # Broadcast notification
    try:
        new_notif = NotificationModel(
            title="New Event!",
            message=f"{db_obj.title} has been organized by {current_user.full_name}",
            type="info"
        )
        db.add(new_notif)
        await db.commit()
        await db.refresh(new_notif)

        await manager.broadcast({
            "type": "notification",
            "title": new_notif.title,
            "message": new_notif.message,
            "notif_type": new_notif.type,
            "id": new_notif.id
        })
    except Exception as e:
        print(f"Notification Error: {e}")

    return db_obj

@router.get("/{id}", response_model=Event)
async def read_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
) -> Any:
    """
    Get event by ID.
    """
    result = await db.execute(select(EventModel).where(EventModel.id == id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.post("/{id}/register")
async def register_participation(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Register for an event.
    """
    from app.services import event_service
    return await event_service.register_for_event(db, current_user.id, id)

@router.put("/{id}", response_model=Event)
async def update_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    event_in: EventUpdate,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update an event.
    """
    result = await db.execute(select(EventModel).where(EventModel.id == id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not current_user.is_superuser and event.organizer_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    update_data = event_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(event, field, update_data[field])
    
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/{id}", response_model=Event)
async def delete_event(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete an event.
    """
    result = await db.execute(select(EventModel).where(EventModel.id == id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not current_user.is_superuser and event.organizer_id != current_user.id:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    await db.delete(event)
    await db.commit()
    return event

@router.post("/{id}/image", response_model=Event)
async def upload_event_image(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    file: UploadFile = File(...),
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload an image for an event.
    Image uploaded to: events/{event_id}/image_{timestamp}
    """
    from app.utils.storage import storage
    
    result = await db.execute(select(EventModel).where(EventModel.id == id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Only organizer or admins can upload image
    if not current_user.is_superuser and event.organizer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ["jpg", "jpeg", "png", "webp"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG/PNG/WEBP allowed.")
    
    # Read file content
    contents = await file.read()
    
    # Try to upload to Supabase
    image_url = storage.upload_event_image(
        event_id=event.id,
        organizer_id=event.organizer_id,
        file_path=file.filename,
        file_content=contents
    )
    
    # Fallback to local storage if Supabase is not configured
    if image_url is None:
        upload_dir = Path("static/events")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"event_{event.id}.{file_extension}"
        file_path = upload_dir / file_name
        with file_path.open("wb") as buffer:
            buffer.write(contents)
        image_url = f"/static/events/{file_name}"
    
    event.image_url = image_url
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

