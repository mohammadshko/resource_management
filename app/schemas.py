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

class ResourceStatusEnum(str, Enum):
    pending = "pending"
    done = "done"
    error = "error"
    duplicated = "duplicated"

class ResourceCreate(BaseModel):
    platform: PlatformEnum
    type: ResourceTypeEnum
    username: str

class ResourceResponse(BaseModel):
    id: int
    platform: str
    type: str
    username: str
    status: ResourceStatusEnum
    process_time: Optional[float] = None
    log: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PaginatedResourceResponse(BaseModel):
    items: List[ResourceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
