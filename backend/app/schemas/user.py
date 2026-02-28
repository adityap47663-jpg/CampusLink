from typing import Optional
from pydantic import BaseModel, EmailStr

# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    interests: Optional[str] = None
    college_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    theme_preference: Optional[str] = "system"
    college_id: Optional[int] = None
    role: Optional[str] = "student"

# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str

# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: Optional[int] = None

    class Config:
        from_attributes = True

# Additional properties to return via API
class User(UserInDBBase):
    events_count: Optional[int] = None
    buddies_count: Optional[int] = None

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None
