import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

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

def test_create_resource_and_check_existing():
    # 1. Create a valid resource (Telegram, channel)
    response = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "channel", "username": "channel_user_1"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["platform"] == "Telegram"
    assert data["type"] == "channel"
    assert data["username"] == "channel_user_1"
    assert data["status"] == "pending"
    assert data["process_time"] is None
    assert data["log"] == ""

    # 2. Add resource with same platform and username
    response2 = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "group", "username": "channel_user_1"}
    )
    assert response2.status_code == 201
    # Returns existing resource record without inserting a second row
    assert response2.json()["id"] == data["id"]
    assert response2.json()["type"] == "channel"

    # Verify database table has only 1 row total
    list_resp = client.get("/api/resources")
    assert list_resp.json()["total"] == 1


def test_invalid_resource_type():
    # Only channel and group are valid types
    response = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "invalid_type", "username": "user1"}
    )
    assert response.status_code == 422


def test_server_side_search_and_pagination():
    # Create test resources
    client.post("/api/resources", json={"platform": "Telegram", "type": "channel", "username": "alpha_user"})
    client.post("/api/resources", json={"platform": "Twitter", "type": "group", "username": "beta_group"})
    client.post("/api/resources", json={"platform": "Instagram", "type": "channel", "username": "gamma_user"})

    # Test default listing
    resp = client.get("/api/resources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["total_pages"] == 1

    # Test search query parameter
    search_resp = client.get("/api/resources?search=Twitter")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["platform"] == "Twitter"

    # Test pagination query parameters
    page_resp = client.get("/api/resources?page=1&page_size=2")
    assert page_resp.status_code == 200
    page_data = page_resp.json()
    assert len(page_data["items"]) == 2
    assert page_data["total"] == 3
    assert page_data["total_pages"] == 2


def test_ui_page_routes():
    res_submit = client.get("/")
    assert res_submit.status_code == 200
    assert "Submit New Resource" in res_submit.text

    res_list = client.get("/list")
    assert res_list.status_code == 200
    assert "Inserted Resources" in res_list.text

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
