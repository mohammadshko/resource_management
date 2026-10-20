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
    description="API for ingesting resource requests, searching platform databases, and processing logs manually.",
    version="1.0.0",
)

# Static and Templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# UI Route
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def get_ui(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# API Endpoints

@app.post(
    "/api/resources",
    response_model=schemas.ResourceLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create resource log and check platform user",
    description="Accepts resource data (platform, type, username). Searches platform database for username; if missing, inserts new row. Then saves log entry with status 'pending'."
)
def create_resource(
    resource: schemas.ResourceCreate,
    db: Session = Depends(get_db)
):
    # Check platform user database
    platform_user = db.query(PlatformUser).filter(
        PlatformUser.platform == resource.platform,
        PlatformUser.username == resource.username
    ).first()

    if not platform_user:
        platform_user = PlatformUser(
            platform=resource.platform,
            username=resource.username
        )
        db.add(platform_user)
        db.commit()
        db.refresh(platform_user)

    # Save resource log with 'pending' status
    log_entry = ResourceLog(
        platform=resource.platform,
        type=resource.type,
        username=resource.username,
        status="pending",
        log=f"Resource request created for {resource.username} on platform {resource.platform} (type: {resource.type})"
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    return log_entry


@app.post(
    "/api/resources/process",
    response_model=List[schemas.ResourceLogResponse],
    summary="Process pending resource logs manually",
    description="Fetches pending logs (or specified list of IDs) from database, processes them, calculates process time, and updates status to 'done' or 'error'."
)
def process_resources(
    batch_req: Optional[schemas.ProcessBatchRequest] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ResourceLog)
    if batch_req and batch_req.ids:
        logs_to_process = query.filter(ResourceLog.id.in_(batch_req.ids)).all()
    else:
        logs_to_process = query.filter(ResourceLog.status == "pending").all()

    processed_logs = []
    for log_item in logs_to_process:
        start_time = time.time()
        try:
            # Simulate processing logic for resource
            # If username contains 'error' or 'fail', simulate an error state
            if "error" in log_item.username.lower() or "fail" in log_item.username.lower():
                raise ValueError(f"Failed to process resource for {log_item.username} on {log_item.platform}")

            # Successful processing simulation
            time.sleep(0.05)  # slight delay to record meaningful process time
            elapsed = round(time.time() - start_time, 4)

            log_item.status = "done"
            log_item.process_time = elapsed
            log_item.log = (log_item.log or "") + f"\n[{utc_now().isoformat()}] Processing completed successfully. Duration: {elapsed}s."
        except Exception as e:
            elapsed = round(time.time() - start_time, 4)
            log_item.status = "error"
            log_item.process_time = elapsed
            log_item.log = (log_item.log or "") + f"\n[{utc_now().isoformat()}] Processing error: {str(e)}"

        log_item.updated_at = utc_now()
        db.add(log_item)
        processed_logs.append(log_item)

    db.commit()
    for item in processed_logs:
        db.refresh(item)

    return processed_logs


@app.post(
    "/api/resources/{resource_id}/process",
    response_model=schemas.ResourceLogResponse,
    summary="Process a specific resource log manually by ID",
    description="Processes a single resource log entry by ID, updates process_time, status ('done' or 'error'), and log messages."
)
def process_resource_by_id(
    resource_id: int,
    db: Session = Depends(get_db)
):
    log_item = db.query(ResourceLog).filter(ResourceLog.id == resource_id).first()
    if not log_item:
        raise HTTPException(status_code=404, detail="Resource log entry not found")

    start_time = time.time()
    try:
        if "error" in log_item.username.lower() or "fail" in log_item.username.lower():
            raise ValueError(f"Failed to process resource for {log_item.username} on {log_item.platform}")

        time.sleep(0.05)
        elapsed = round(time.time() - start_time, 4)

        log_item.status = "done"
        log_item.process_time = elapsed
        log_item.log = (log_item.log or "") + f"\n[{utc_now().isoformat()}] Manual processing completed. Duration: {elapsed}s."
    except Exception as e:
        elapsed = round(time.time() - start_time, 4)
        log_item.status = "error"
        log_item.process_time = elapsed
        log_item.log = (log_item.log or "") + f"\n[{utc_now().isoformat()}] Manual processing error: {str(e)}"

    log_item.updated_at = utc_now()
    db.add(log_item)
    db.commit()
    db.refresh(log_item)

    return log_item


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
