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

def test_create_resource_and_duplicate_entry():
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

    # Duplicate submission inserts new entry with status 'duplicated'
    response2 = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "group", "username": "channel_user_1"}
    )
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["id"] != data["id"]
    assert data2["status"] == "duplicated"

    # Verify 2 entries in total (1 pending, 1 duplicated)
    list_resp = client.get("/api/resources")
    assert list_resp.json()["total"] == 2


def test_invalid_resource_type():
    response = client.post(
        "/api/resources",
        json={"platform": "Telegram", "type": "invalid_type", "username": "user1"}
    )
    assert response.status_code == 422


def test_filters_and_sorting():
    client.post("/api/resources", json={"platform": "Telegram", "type": "channel", "username": "alpha_user"})
    client.post("/api/resources", json={"platform": "Twitter", "type": "group", "username": "beta_group"})
    client.post("/api/resources", json={"platform": "Instagram", "type": "channel", "username": "gamma_user"})

    # Test platform filter
    resp = client.get("/api/resources?platform=Telegram")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["platform"] == "Telegram"

    # Test status filter
    resp_status = client.get("/api/resources?status=pending")
    assert resp_status.status_code == 200
    assert resp_status.json()["total"] == 3

    # Test sort_by and sort_order
    resp_sort = client.get("/api/resources?sort_by=username&sort_order=asc")
    assert resp_sort.status_code == 200
    items = resp_sort.json()["items"]
    assert items[0]["username"] == "alpha_user"
    assert items[1]["username"] == "beta_group"
    assert items[2]["username"] == "gamma_user"


def test_ui_page_routes():
    res_submit = client.get("/")
    assert res_submit.status_code == 200

    res_list = client.get("/list")
    assert res_list.status_code == 200
    assert "Platform:" in res_list.text
    assert "Status:" in res_list.text
    assert "Duplicated" in res_list.text

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
