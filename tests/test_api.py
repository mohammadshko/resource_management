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

def test_create_resource_with_enums_and_check_platform_user():
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

    # Verify platform user was inserted
    users_resp = client.get("/api/platform-users")
    assert users_resp.status_code == 200
    users = users_resp.json()
    assert len(users) == 1
    assert users[0]["platform"] == "Telegram"
    assert users[0]["username"] == "channel_user_1"

    # 2. Add another resource with same platform and username (type: group)
    response2 = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "group", "username": "channel_user_1"}
    )
    assert response2.status_code == 201
    assert response2.json()["type"] == "group"

    # Verify platform user count is still 1 (no duplicate inserted)
    users_resp2 = client.get("/api/platform-users")
    assert len(users_resp2.json()) == 1


def test_invalid_resource_type():
    # Only channel and group are valid types
    response = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "invalid_type", "username": "user1"}
    )
    assert response.status_code == 422


def test_ui_page_routes():
    res_submit = client.get("/")
    assert res_submit.status_code == 200
    assert "Submit New Resource" in res_submit.text
    assert "channel" in res_submit.text
    assert "group" in res_submit.text

    res_list = client.get("/list")
    assert res_list.status_code == 200
    assert "Inserted Resources" in res_list.text

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
