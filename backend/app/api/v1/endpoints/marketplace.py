from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.api import deps
from app.db.session import get_db
from app.models.models import MarketplaceItem as MIModel, User as UserModel
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class MIResponse(BaseModel):
    id: int
    owner_id: int
    title: str
    description: str
    price: float
    category: str
    image_url: str | None
    is_available: bool
    created_at: datetime
    owner_name: str | None = None

    class Config:
        from_attributes = True

@router.get("/", response_model=List[MIResponse])
async def read_items(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    result = await db.execute(
        select(MIModel, UserModel.full_name)
        .join(UserModel, MIModel.owner_id == UserModel.id)
        .where(MIModel.is_available == True)
        .offset(skip).limit(limit)
    )
    
    items = []
    for row in result:
        item, owner_name = row
        item_dict = MIResponse.model_validate(item)
        item_dict.owner_name = owner_name
        items.append(item_dict)
    return items

@router.post("/", response_model=MIResponse)
async def create_item(
    *,
    db: AsyncSession = Depends(get_db),
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(0.0),
    category: str = Form("other"),
    file: UploadFile | None = File(None),
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a marketplace item.
    Image uploaded to: marketplace/{user_id}/items/{item_id}/{filename}
    """
    from app.utils.storage import storage
    
    # Create item first (without image URL) to get the ID
    db_obj = MIModel(
        owner_id=current_user.id,
        title=title,
        description=description,
        price=price,
        category=category,
        image_url=None
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    
    # Now upload image if provided
    if file:
        ext = file.filename.split(".")[-1].lower()
        if ext not in ["jpg", "jpeg", "png", "webp"]:
            raise HTTPException(status_code=400, detail="Invalid file type. Only JPG/PNG/WEBP allowed.")
        
        contents = await file.read()
        
        # Try to upload to Supabase
        image_url = storage.upload_marketplace_item(
            user_id=current_user.id,
            item_id=db_obj.id,
            file_path=file.filename,
            file_content=contents
        )
        
        # Fallback to local storage if Supabase is not configured
        if image_url is None:
            upload_dir = Path("static/marketplace")
            upload_dir.mkdir(parents=True, exist_ok=True)
            safe_name = f"{current_user.id}_{file.filename}"
            image_path = f"static/marketplace/{safe_name}"
            with open(image_path, "wb") as buffer:
                buffer.write(contents)
            image_url = image_path.replace("\\", "/")
        
        # Update item with image URL
        db_obj.image_url = image_url
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
    
    return db_obj

@router.delete("/{id}")
async def delete_item(
    *,
    db: AsyncSession = Depends(get_db),
    id: int,
    current_user: UserModel = Depends(deps.get_current_active_user),
) -> Any:
    result = await db.execute(select(MIModel).where(MIModel.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if not current_user.is_superuser and item.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    await db.delete(item)
    await db.commit()
    return {"message": "Item deleted"}
