import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import ResourceLog, PlatformUser

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_create_resource_and_platform_user_search():
    # 1. Create a new resource
    response = client.post(
        "/api/resources",
        json={"platform": "github", "type": "repo", "username": "user1"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "github"
    assert data["username"] == "user1"
    assert data["status"] == "pending"

    # Verify platform user was inserted
    users_resp = client.get("/api/platform-users")
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert len(users) == 1
    assert users[0]["platform"] == "github"
    assert users[0]["username"] == "user1"

    # 2. Add another resource with same platform and username
    response2 = client.post(
        "/api/resources",
        json={"platform": "github", "type": "gist", "username": "user1"}
    )
    assert response2.status_code == 201

    # Verify platform user count is still 1 (no duplicate inserted)
    users_resp2 = client.get("/api/platform-users")
    assert len(users_resp2.json()) == 1


def test_process_resources_done_and_error():
    # Create two resources (one normal, one with 'error' in username)
    client.post("/api/resources", json={"platform": "aws", "type": "s3", "username": "normal_user"})
    client.post("/api/resources", json={"platform": "aws", "type": "ec2", "username": "error_user"})

    # Process pending resources
    proc_resp = client.post("/api/resources/process")
    assert proc_resp.status_code == 200
    processed = proc_resp.json()
    assert len(processed) == 2

    # Check statuses
    statuses = {item["username"]: item for item in processed}
    assert statuses["normal_user"]["status"] == "done"
    assert statuses["normal_user"]["process_time"] is not None
    assert statuses["normal_user"]["process_time"] > 0

    assert statuses["error_user"]["status"] == "error"
    assert "Processing error" in statuses["error_user"]["log"]


def test_process_resource_by_id():
    res = client.post("/api/resources", json={"platform": "gcp", "type": "storage", "username": "gcp_user"})
    log_id = res.json()["id"]

    proc_res = client.post(f"/api/resources/{log_id}/process")
    assert proc_res.status_code == 200
    data = proc_res.json()
    assert data["id"] == log_id
    assert data["status"] == "done"
    assert data["process_time"] is not None


def test_ui_and_docs_endpoints():
    res_ui = client.get("/")
    assert res_ui.status_code == 200
    assert "Resource Management System" in res_ui.text

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
