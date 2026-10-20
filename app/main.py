import time
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import ResourceLog, PlatformUser
from app import schemas

def utc_now():
    return datetime.now(timezone.utc)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resource Management API",
    description="API for ingesting resource requests, searching platform databases, and managing logs.",
    version="1.0.0",
)

# Static and Templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# UI Routes
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_submit_page(request: Request):
    return templates.TemplateResponse(request=request, name="submit.html")

@app.get("/list", response_class=HTMLResponse, include_in_schema=False)
def get_list_page(request: Request):
    return templates.TemplateResponse(request=request, name="list.html")


# API Endpoints

@app.post(
    "/api/resources",
    response_model=schemas.ResourceLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create resource log and check platform user",
    description="Accepts resource data (platform enum, type enum ['channel', 'group'], username). Searches platform database for username; if missing, inserts new row. Saves log entry with status 'pending' and empty log."
)
def create_resource(
    resource: schemas.ResourceCreate,
    db: Session = Depends(get_db)
):
    platform_val = resource.platform.value if hasattr(resource.platform, 'value') else str(resource.platform)
    type_val = resource.type.value if hasattr(resource.type, 'value') else str(resource.type)

    # Check platform user database
    platform_user = db.query(PlatformUser).filter(
        PlatformUser.platform == platform_val,
        PlatformUser.username == resource.username
    ).first()

    if not platform_user:
        platform_user = PlatformUser(
            platform=platform_val,
            username=resource.username
        )
        db.add(platform_user)
        db.commit()
        db.refresh(platform_user)

    # Save resource log with 'pending' status, empty log and empty process_time
    log_entry = ResourceLog(
        platform=platform_val,
        type=type_val,
        username=resource.username,
        status="pending",
        process_time=None,
        log=""
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return log_entry


@app.get(
    "/api/resources",
    response_model=List[schemas.ResourceLogResponse],
    summary="List resource logs",
    description="Retrieve all resource log entries, optionally filtered by status or platform."
)
def get_resources(
    status: Optional[str] = None,
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ResourceLog)
    if status:
        query = query.filter(ResourceLog.status == status)
    if platform:
        query = query.filter(ResourceLog.platform == platform)
    return query.order_by(ResourceLog.id.desc()).all()


@app.get(
    "/api/platform-users",
    response_model=List[schemas.PlatformUserResponse],
    summary="List platform users",
    description="Retrieve all registered platform users."
)
def get_platform_users(
    platform: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PlatformUser)
    if platform:
        query = query.filter(PlatformUser.platform == platform)
    return query.order_by(PlatformUser.id.desc()).all()
