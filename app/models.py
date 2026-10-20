from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, UniqueConstraint
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class ResourceLog(Base):
    __tablename__ = "resource_logs"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True, nullable=False)
    type = Column(String, nullable=False)
    username = Column(String, index=True, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, done, error
    process_time = Column(Float, nullable=True)  # in seconds, updated by operator/db
    log = Column(Text, nullable=True)  # log messages, empty on insert
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class PlatformUser(Base):
    __tablename__ = "platform_users"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String, index=True, nullable=False)
    username = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint('platform', 'username', name='_platform_username_uc'),
    )
