from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class PlatformEnum(str, Enum):
    telegram = "Telegram"
    twitter = "Twitter"
    instagram = "Instagram"
    youtube = "YouTube"
    discord = "Discord"

class ResourceTypeEnum(str, Enum):
    channel = "channel"
    group = "group"

class ResourceCreate(BaseModel):
    platform: PlatformEnum
    type: ResourceTypeEnum
    username: str

class ResourceProcessResponse(BaseModel):
    id: int
    platform: str
    type: str
    username: str
    status: str
    process_time: Optional[float] = None
    log: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ResourceLogResponse(BaseModel):
    id: int
    platform: str
    type: str
    username: str
    status: str
    process_time: Optional[float] = None
    log: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PlatformUserResponse(BaseModel):
    id: int
    platform: str
    username: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProcessBatchRequest(BaseModel):
    ids: Optional[List[int]] = None
