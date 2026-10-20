from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SQLEnum
from app.database import Base
from app.schemas import PlatformEnum, ResourceTypeEnum, ResourceStatusEnum

def utc_now():
    return datetime.now(timezone.utc)

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(SQLEnum(PlatformEnum, native_enum=False), index=True, nullable=False)
    type = Column(SQLEnum(ResourceTypeEnum, native_enum=False), nullable=False)
    username = Column(String, index=True, nullable=False)
    status = Column(SQLEnum(ResourceStatusEnum, native_enum=False), default=ResourceStatusEnum.pending, nullable=False)
    process_time = Column(Float, nullable=True)  # in seconds
    log = Column(Text, nullable=True)  # log column
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
