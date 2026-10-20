import math
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import Resource
from app import schemas

def utc_now():
    return datetime.now(timezone.utc)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resource Management API",
    description="API for ingesting resource requests, managing resources, status, process_time, and logs.",
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
    response_model=schemas.ResourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Get resource data and insert if missing",
    description="Accepts resource data (platform enum, type enum ['channel', 'group'], username). Checks database for username per platform and inserts new row if missing."
)
def create_resource(
    resource: schemas.ResourceCreate,
    db: Session = Depends(get_db)
):
    platform_val = resource.platform.value if hasattr(resource.platform, 'value') else str(resource.platform)
    type_val = resource.type.value if hasattr(resource.type, 'value') else str(resource.type)

    existing = db.query(Resource).filter(
        Resource.platform == platform_val,
        Resource.username == resource.username
    ).first()

    if existing:
        return existing

    new_resource = Resource(
        platform=platform_val,
        type=type_val,
        username=resource.username,
        status="pending",
        process_time=None,
        log=""
    )
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)

    return new_resource


@app.get(
    "/api/resources",
    response_model=schemas.PaginatedResourceResponse,
    summary="List resources with search, filters, sorting, and pagination",
    description="Retrieve paginated resource entries with server-side search, platform filter, status filter, sorting options, and pagination."
)
def get_resources(
    search: Optional[str] = Query(None, description="Search term for platform, type, username, status, or log"),
    platform: Optional[str] = Query(None, description="Filter by platform name"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (pending, done, error)"),
    sort_by: Optional[str] = Query("id", description="Sort by field: id, created_at, platform, status, username"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    query = db.query(Resource)

    if platform and platform.strip():
        query = query.filter(Resource.platform.ilike(f"%{platform.strip()}%"))

    if status_filter and status_filter.strip():
        query = query.filter(Resource.status.ilike(f"%{status_filter.strip()}%"))

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Resource.platform.ilike(term),
                Resource.type.ilike(term),
                Resource.username.ilike(term),
                Resource.status.ilike(term),
                Resource.log.ilike(term)
            )
        )

    # Sorting logic
    sort_field = getattr(Resource, sort_by, Resource.id) if sort_by in ["id", "created_at", "platform", "status", "username"] else Resource.id
    if sort_order and sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return schemas.PaginatedResourceResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
