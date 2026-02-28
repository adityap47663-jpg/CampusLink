from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    invite_code = Column(String, unique=True)
    slug = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    students = relationship("User", back_populates="college", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="college", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="student") # super_admin, college_admin, student
    
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True)
    college = relationship("College", back_populates="students")

    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    interests = Column(String, nullable=True)
    college_name = Column(String, nullable=True)
    profile_image_url = Column(String, nullable=True)
    theme_preference = Column(String, default="system")
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    
    events_count = Column(Integer, default=0)
    buddies_count = Column(Integer, default=0)
    
    # Relationships
    organized_events = relationship("Event", back_populates="organizer", cascade="all, delete-orphan")
    participations = relationship("Participation", back_populates="user", cascade="all, delete-orphan")
    travel_plans = relationship("TravelPlan", back_populates="organizer", cascade="all, delete-orphan")
    messages_sent = relationship("Message", back_populates="sender", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    location = Column(String)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    image_url = Column(String, nullable=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    college_id = Column(Integer, ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organizer = relationship("User", back_populates="organized_events")
    college = relationship("College", back_populates="events")
    participants = relationship("Participation", back_populates="event", cascade="all, delete-orphan")

class Participation(Base):
    __tablename__ = "participations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="registered") # registered, attended, cancelled

    user = relationship("User", back_populates="participations")
    event = relationship("Event", back_populates="participants")

class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    category = Column(String) # Technical, Cultural, Sports, etc.
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Community(Base):
    __tablename__ = "communities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    member_count = Column(Integer, default=0)
    image_url = Column(String, nullable=True)

class TravelPlan(Base):
    __tablename__ = "travel_plans"

    id = Column(Integer, primary_key=True, index=True)
    destination = Column(String, nullable=False)
    date_time = Column(DateTime(timezone=True), nullable=False)
    mode = Column(String) # Car, Bus, Auto, etc.
    seats_available = Column(Integer, default=1)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    organizer = relationship("User", back_populates="travel_plans")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    channel = Column(String, index=True) # group name or "general"

    sender = relationship("User", back_populates="messages_sent")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True) # Null for broadcast
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, default="info") # info, success, warning, error
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MarketplaceItem(Base):
    __tablename__ = "marketplace_items"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    title = Column(String, index=True)
    description = Column(Text)
    price = Column(Float, default=0.0) # 0 for "free/lend"
    category = Column(String) # books, electronics, etc.
    image_url = Column(String, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User")

class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    id_card_url = Column(String)
    status = Column(String, default="pending") # pending, approved, rejected
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
